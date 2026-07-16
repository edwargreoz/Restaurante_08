from django.db import transaction
from django.utils import timezone
from decimal import Decimal
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.db.models import Q

from core.excepciones import (
    MesaConComandaActiva, CajaNoAbierta, RecursoNoEncontrado,
    StockInsuficiente, TransicionEstadoInvalida, PlatoNoDisponible,
    ComandaNoDisponible, MontoInvalido, ReferenciaInvalida,
)
from pedidos.models import Comanda, LineaComanda
from mesas.models import Mesa, UnionMesa
from caja.models import Caja, Pago
from inventario.models import RecetaInsumo, MovimientoInsumo, convertir_unidad
from menu.models import Plato



class ComandaService:
    """Toda la lógica de negocio relacionada a comandas."""

    @staticmethod
    @transaction.atomic
    def abrir(mesa_id: int, usuario) -> Comanda:
        caja_abierta = Caja.objects.filter(estado='ABIERTA').exists()
        if not caja_abierta:
            raise CajaNoAbierta('No hay un turno de caja abierto. Abre caja primero.')

        mesa = Mesa.objects.select_for_update().filter(id=mesa_id, activo=True).first()
        if not mesa:
            raise RecursoNoEncontrado('Mesa no encontrada')

        comanda_existente = Comanda.objects.filter(
            mesa=mesa, estado__in=['ABIERTA', 'EN_PREPARACION', 'LISTA']
        ).first()
        if comanda_existente:
            return comanda_existente

        if mesa.estado not in ['LIBRE', 'RESERVADA']:
            raise MesaConComandaActiva('La mesa no está libre ni reservada')

        union = UnionMesa.objects.filter(mesas=mesa, activo=True).first()
        if union:
            for m in union.mesas.all():
                comanda_m = Comanda.objects.filter(
                    mesa=m, estado__in=['ABIERTA', 'EN_PREPARACION', 'LISTA']
                ).first()
                if comanda_m:
                    return comanda_m
                if m.estado not in ['LIBRE', 'RESERVADA']:
                    raise MesaConComandaActiva(
                        f'La mesa {m.numero} de la unión no está libre ni reservada'
                    )

        comanda = Comanda.objects.create(mesa=mesa, mozo=usuario)
        mesa.estado = 'OCUPADA'
        mesa.save(update_fields=['estado'])

        if union:
            for m in union.mesas.all():
                if m.id != mesa.id:
                    m.estado = 'OCUPADA'
                    m.save(update_fields=['estado'])

        _notificar_plano()
        return comanda

    @staticmethod
    @transaction.atomic
    def agregar_platos(comanda_id: int, platos_data: list, usuario=None) -> list:
        comanda = Comanda.objects.select_for_update().get(id=comanda_id)
        if comanda.estado not in ('ABIERTA', 'LISTA'):
            raise ComandaNoDisponible('La comanda no está abierta')
        errores = []
        platos_a_crear = []
        movimientos = []

        for item in platos_data:
            plato_id = item.get('plato_id')
            cantidad = item.get('cantidad', 1)
            observacion = item.get('observacion', '')

            plato = Plato.objects.filter(id=plato_id, activo=True).first()
            if not plato:
                errores.append({'plato_id': plato_id, 'error': 'Plato no encontrado'})
                continue
            if not plato.disponible:
                errores.append({'plato_id': plato_id, 'error': 'Plato no disponible'})
                continue
            if not plato.receta_id:
                errores.append({
                    'plato_id': plato_id,
                    'plato': plato.nombre,
                    'error': 'El plato no tiene una receta asignada'
                })
                continue

            recetas = plato.receta.insumos.select_related(
                'insumo'
            ).select_for_update(of=('insumo',))
            faltantes = []
            deducciones = []

            for receta in recetas:
                insumo = receta.insumo
                necesario_en_unidad_receta = receta.cantidad_por_porcion * Decimal(str(cantidad))
                necesario = convertir_unidad(
                    necesario_en_unidad_receta,
                    receta.unidad,
                    insumo.unidad
                )
                if insumo.stock_actual < necesario:
                    faltantes.append(
                        f"{insumo.nombre}: disponible {insumo.stock_actual} {insumo.unidad}, "
                        f"necesario {necesario} {insumo.unidad}"
                    )
                    continue

                stock_anterior = insumo.stock_actual
                insumo.stock_actual -= necesario
                insumo.save(update_fields=['stock_actual'])

                deducciones.append(MovimientoInsumo(
                    insumo=insumo, comanda=comanda,
                    tipo='DEDUCCION', cantidad=necesario,
                    stock_anterior=stock_anterior,
                    stock_posterior=insumo.stock_actual,
                    usuario=usuario,
                    observacion=f"Plato: {plato.nombre} x{cantidad}"
                ))

            if faltantes:
                errores.append({
                    'plato_id': plato_id, 'plato': plato.nombre,
                    'error': 'Stock insuficiente', 'detalle': faltantes
                })
                continue

            movimientos.extend(deducciones)
            platos_a_crear.append(LineaComanda(
                comanda=comanda, plato=plato,
                cantidad=cantidad, observacion=observacion,
            ))

        if errores:
            raise StockInsuficiente({'errores': errores})

        LineaComanda.objects.bulk_create(platos_a_crear)
        MovimientoInsumo.objects.bulk_create(movimientos)

        # --- Regla InsumoAgotado ---
        # Si algún insumo llegó a 0, marcar los platos que lo usan como no disponibles
        insumos_agotados = set()
        for mov in movimientos:
            if mov.stock_posterior <= 0:
                insumos_agotados.add(mov.insumo_id)

        if insumos_agotados:
            platos_afectados = Plato.objects.filter(
                receta__insumos__insumo_id__in=insumos_agotados,
                disponible=True,
            ).distinct()
            platos_afectados.update(disponible=False)

        _notificar_comanda(comanda.id)
        return platos_a_crear

    @staticmethod
    @transaction.atomic
    def fusionar(comanda_id: int, otra_comanda_id: int) -> Comanda:
        comanda = Comanda.objects.select_for_update().get(id=comanda_id)
        otra = Comanda.objects.select_for_update().get(id=otra_comanda_id)

        if comanda.estado in ('COBRADA', 'ANULADA'):
            raise ComandaNoDisponible('La comanda principal no está activa')
        if otra.estado in ('COBRADA', 'ANULADA'):
            raise ComandaNoDisponible('La comanda a fusionar no está activa')

        LineaComanda.objects.filter(comanda=otra).update(comanda=comanda)
        otra.estado = 'ANULADA'
        otra.fecha_cierre = timezone.now()
        otra.save(update_fields=['estado', 'fecha_cierre'])
        return comanda

    @staticmethod
    @transaction.atomic
    def anular(comanda_id: int, usuario=None) -> Comanda:
        comanda = Comanda.objects.select_for_update().get(id=comanda_id)
        if comanda.estado == 'COBRADA':
            raise ComandaNoDisponible('No se puede anular una comanda ya cobrada')
        if comanda.estado == 'ANULADA':
            raise ComandaNoDisponible('La comanda ya está anulada')

        lineas = comanda.lineas.select_related('plato__receta').all()
        movimientos = []
        for linea in lineas:
            if not linea.plato.receta_id:
                continue
            recetas = linea.plato.receta.insumos.select_related(
                'insumo'
            ).select_for_update(of=('insumo',))
            for receta in recetas:
                insumo = receta.insumo
                cantidad = receta.cantidad_por_porcion * Decimal(str(linea.cantidad))
                cantidad_a_restaurar = convertir_unidad(
                    cantidad, receta.unidad, insumo.unidad
                )
                stock_anterior = insumo.stock_actual
                insumo.stock_actual += cantidad_a_restaurar
                insumo.save(update_fields=['stock_actual'])
                movimientos.append(MovimientoInsumo(
                    insumo=insumo, comanda=comanda,
                    tipo='REPOSICION', cantidad=cantidad_a_restaurar,
                    stock_anterior=stock_anterior,
                    stock_posterior=insumo.stock_actual,
                    usuario=usuario,
                    observacion=f"Anulación comanda #{comanda.id}"
                ))

        MovimientoInsumo.objects.bulk_create(movimientos)
        comanda.estado = 'ANULADA'
        comanda.fecha_cierre = timezone.now()
        comanda.save(update_fields=['estado', 'fecha_cierre'])

        _liberar_mesas(comanda)
        _notificar_plano()
        _notificar_comanda(comanda.id)
        return comanda

    @staticmethod
    @transaction.atomic
    def pagar(comanda_id: int, metodo: str, monto, vuelto=0,
              referencia='', caja=None) -> Comanda:
        comanda = Comanda.objects.select_for_update().get(id=comanda_id)
        if comanda.estado != 'LISTA':
            raise ComandaNoDisponible('La comanda no está lista para pagar')

        monto = Decimal(str(monto))
        if monto < comanda.total - Decimal('0.01'):
            raise MontoInvalido(
                f'El monto recibido ({monto}) es menor al total ({comanda.total})'
            )

        if metodo == 'TARJETA':
            _validar_referencia_tarjeta(referencia)

        Pago.objects.create(
            comanda=comanda, metodo=metodo,
            monto=monto, vuelto=vuelto, referencia=referencia, caja=caja
        )
        comanda.estado = 'COBRADA'
        comanda.fecha_cierre = timezone.now()
        comanda.save(update_fields=['estado', 'fecha_cierre'])

        _finalizar_reservas_comanda(comanda)
        _actualizar_estado_mesa_post_pago(comanda)
        _notificar_plano()
        _notificar_comanda(comanda.id)
        return comanda

    @staticmethod
    @transaction.atomic
    def pagar_split(comanda_id: int, pagos_lista: list, caja=None) -> Comanda:
        comanda = Comanda.objects.select_for_update().get(id=comanda_id)
        if comanda.estado != 'LISTA':
            raise ComandaNoDisponible('La comanda no está lista para pagar')

        for pd in pagos_lista:
            pd['monto'] = Decimal(str(pd['monto']))
            pd['vuelto'] = Decimal(str(pd.get('vuelto', 0) or 0))

        total_pagos = sum(p['monto'] for p in pagos_lista)
        if abs(total_pagos - comanda.total) > Decimal('0.01'):
            raise MontoInvalido(
                f'Suma de pagos ({total_pagos}) no coincide con total ({comanda.total})'
            )

        for pd in pagos_lista:
            if pd.get('metodo') == 'TARJETA':
                _validar_referencia_tarjeta(pd.get('referencia', ''))
            Pago.objects.create(
                comanda=comanda, metodo=pd['metodo'],
                monto=pd['monto'], vuelto=pd.get('vuelto', 0),
                referencia=pd.get('referencia', ''), caja=caja
            )

        comanda.estado = 'COBRADA'
        comanda.fecha_cierre = timezone.now()
        comanda.save(update_fields=['estado', 'fecha_cierre'])

        _finalizar_reservas_comanda(comanda)
        _actualizar_estado_mesa_post_pago(comanda)
        _notificar_plano()
        _notificar_comanda(comanda.id)
        return comanda


class LineaComandaService:
    """Lógica de líneas de comanda (KDS)."""

    @staticmethod
    @transaction.atomic
    def enviar_cocina(linea_id: int)->LineaComanda:
        linea = LineaComanda.objects.select_for_update().get(id = linea_id)
        if linea.estado != 'PENDIENTE':
            raise TransicionEstadoInvalida(
                'Solo se puede enviar a cocina en estado PENDIENTE'
            )
        linea.estado = 'EN_PREP'
        linea.save(update_fields=['estado'])

        comanda = linea.comanda
        lineas = list(comanda.lineas.select_related('plato').all())
        if all(l.estado == 'EN_PREP' for l in lineas):
            comanda.estado = 'EN_PREPARACION'
            comanda.save(update_fields=['estado'])

        _notificar_kds()
        return linea
       

    @staticmethod
    @transaction.atomic
    def marcar_listo(linea_id: int) -> LineaComanda:
        linea = LineaComanda.objects.select_for_update().get(id=linea_id)
        if linea.estado != 'EN_PREP':
            raise TransicionEstadoInvalida(
                'Solo se puede marcar LISTO una línea EN_PREPARACION'
            )
        linea.estado = 'LISTO'
        linea.save(update_fields=['estado'])

        comanda = linea.comanda
        lineas = list(comanda.lineas.select_related('plato').all())
        if all(l.estado == 'LISTO' for l in lineas):
            comanda.estado = 'LISTA'
            comanda.save(update_fields=['estado'])

        _notificar_kds()
        _notificar_plano()
        return linea
    @staticmethod
    def obtener_panel_kds():
        """Retorna comandas activas para el panel de cocina (KDS)."""
        comanda_ids = LineaComanda.objects.filter(
            estado__in=['PENDIENTE', 'EN_PREP']
        ).values_list('comanda_id', flat=True).distinct()
        return Comanda.objects.filter(
            Q(estado='EN_PREPARACION') | Q(id__in=comanda_ids)
        ).prefetch_related('lineas__plato', 'mozo', 'mesa').order_by('fecha_apertura')

    @staticmethod
    def obtener_comandas_con_lineas_pendientes():
        """Retorna IDs de comandas que tienen líneas PENDIENTE o EN_PREP."""
        return LineaComanda.objects.filter(
            estado__in=['PENDIENTE', 'EN_PREP']
        ).values_list('comanda_id', flat=True).distinct()


# --- Funciones auxiliares privadas del módulo ---

def _validar_referencia_tarjeta(referencia: str):
    if not referencia or len(referencia.strip()) < 4:
        raise ReferenciaInvalida(
            'Para pagos con tarjeta ingresa los últimos 4 dígitos'
        )
    digitos = ''.join(c for c in referencia if c.isdigit())
    if len(digitos) < 4:
        raise ReferenciaInvalida(
            'La referencia debe contener al menos 4 dígitos de la tarjeta'
        )


def _finalizar_reservas_comanda(comanda):
    from reservas.models import Reserva
    from reservas.services import ReservaService
    mesa = comanda.mesa
    union = UnionMesa.objects.filter(mesas=mesa, activo=True).first()
    for r in Reserva.objects.filter(mesa=mesa, activo=True):
        ReservaService.finalizar(r.id)
    if union:
        for r in Reserva.objects.filter(union_mesa=union, activo=True):
            ReservaService.finalizar(r.id)


def _actualizar_estado_mesa_post_pago(comanda):
    mesa = comanda.mesa
    union = UnionMesa.objects.filter(mesas=mesa, activo=True).first()
    tiene_reserva = mesa.reservas.filter(activo=True).exists()
    if union:
        tiene_reserva = tiene_reserva or union.reservas.filter(activo=True).exists()
    mesa.estado = 'RESERVADA' if tiene_reserva else 'LIMPIEZA'
    mesa.save(update_fields=['estado'])
    if union:
        for m in union.mesas.all():
            if m.id != mesa.id:
                tiene_r = m.reservas.filter(activo=True).exists() or union.reservas.filter(activo=True).exists()
                m.estado = 'RESERVADA' if tiene_r else 'LIMPIEZA'
                m.save(update_fields=['estado'])


def _liberar_mesas(comanda):
    mesa = comanda.mesa
    union = UnionMesa.objects.filter(mesas=mesa, activo=True).first()
    mesas_a_liberar = [mesa]
    if union:
        mesas_a_liberar = list(union.mesas.all())
    for m in mesas_a_liberar:
        tiene_otra = Comanda.objects.filter(
            mesa=m, estado__in=['ABIERTA', 'EN_PREPARACION', 'LISTA']
        ).exclude(id=comanda.id).exists()
        if not tiene_otra:
            tiene_reserva = m.reservas.filter(activo=True).exists()
            if union:
                tiene_reserva = tiene_reserva or union.reservas.filter(activo=True).exists()
            m.estado = 'RESERVADA' if tiene_reserva else 'LIBRE'
            m.save(update_fields=['estado'])


def _notificar_kds():
    try:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            'kds', {'type': 'kds_update', 'data': {'action': 'refresh'}}
        )
    except (ConnectionError, OSError, TimeoutError):
        pass

def _notificar_comanda(comanda_id: int):
    """Notifica al WebSocket de una comanda específica."""
    try:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'comanda_{comanda_id}',
            {'type': 'comanda_update', 'data': {'action': 'refresh', 'comanda_id': comanda_id}}
        )
    except (ConnectionError, OSError, TimeoutError):
        pass

def _notificar_plano():
    from mesas.services import _notificar_plano as notificar
    notificar()

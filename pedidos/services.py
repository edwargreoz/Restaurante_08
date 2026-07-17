from django.db import transaction
from django.utils import timezone
from decimal import Decimal
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.db.models import Q

from core.excepciones import (
    MesaConComandaActiva, CajaNoAbierta, RecursoNoEncontrado,
    StockInsuficiente, TransicionEstadoInvalida,
    ComandaNoDisponible, MontoInvalido, ReferenciaInvalida,
)
from dominio.puertos.repositorios import (
    IComandaRepository, IMesaRepository, ILineaComandaRepository,
)
from pedidos.models import Comanda, LineaComanda
from mesas.models import Mesa, UnionMesa
from caja.models import Caja, Pago
from inventario.models import MovimientoInsumo, convertir_unidad
from menu.models import Plato



class ComandaService:
    """Toda la lógica de negocio relacionada a comandas."""

    def __init__(self, comanda_repo: IComandaRepository,
                 mesa_repo: IMesaRepository):
        self.comanda_repo = comanda_repo
        self.mesa_repo = mesa_repo

    @transaction.atomic
    def abrir(self, mesa_id: int, usuario) -> Comanda:
        from infraestructura.container import get_container
        caja_abierta = get_container().caja_service.repo.existe_abierta()
        if not caja_abierta:
            raise CajaNoAbierta('No hay un turno de caja abierto. Abre caja primero.')

        mesa = self.mesa_repo.obtener_con_bloqueo(mesa_id)
        if not mesa:
            raise RecursoNoEncontrado('Mesa no encontrada')

        comandas_mesa = self.comanda_repo.listar_por_mesa(mesa_id)
        comanda_existente = next((c for c in comandas_mesa if c.estado in ['ABIERTA', 'EN_PREPARACION', 'LISTA']), None)
        if comanda_existente:
            return self.comanda_repo.obtener_por_id(comanda_existente.id)

        if mesa.estado not in ['LIBRE', 'RESERVADA']:
            raise MesaConComandaActiva('La mesa no está libre ni reservada')

        union = get_container().union_mesa_service.repo.obtener_por_mesa(mesa.id) if hasattr(get_container().union_mesa_service, 'repo') else None
        if not union:
            from mesas.models import UnionMesa
            union = UnionMesa.objects.filter(mesas=mesa.id, activo=True).first()
        if union:
            for m in union.mesas.all():
                comandas_m = self.comanda_repo.listar_por_mesa(m.id)
                comanda_m = next((c for c in comandas_m if c.estado in ['ABIERTA', 'EN_PREPARACION', 'LISTA']), None)
                if comanda_m:
                    return self.comanda_repo.obtener_por_id(comanda_m.id)
                if m.estado not in ['LIBRE', 'RESERVADA']:
                    raise MesaConComandaActiva(
                        f'La mesa {m.numero} de la unión no está libre ni reservada'
                    )

        from dominio.entidades.comanda import Comanda
        comanda = self.comanda_repo.guardar(Comanda(mesa_id=mesa.id, mozo_id=usuario.id, estado='ABIERTA', total=0))
        mesa.estado = 'OCUPADA'
        mesa.save(update_fields=['estado'])

        if union:
            for m in union.mesas.all():
                if m.id != mesa.id:
                    m.estado = 'OCUPADA'
                    m.save(update_fields=['estado'])

        _notificar_plano()
        return comanda

    @transaction.atomic
    def agregar_platos(self, comanda_id: int, platos_data: list, usuario=None) -> list:
        from infraestructura.container import get_container
        comanda = self.comanda_repo.obtener_con_bloqueo(comanda_id)
        if comanda.estado not in ('ABIERTA', 'LISTA'):
            raise ComandaNoDisponible('La comanda no está abierta')
        errores = []
        platos_a_crear = []
        movimientos = []

        for item in platos_data:
            plato_id = item.get('plato_id')
            cantidad = item.get('cantidad', 1)
            observacion = item.get('observacion', '')

            plato = get_container().plato_service.plato_repo.obtener_por_id(plato_id)
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
                try:
                    necesario = convertir_unidad(
                        necesario_en_unidad_receta,
                        receta.unidad,
                        insumo.unidad
                    )
                except (ValueError, KeyError) as e:
                    faltantes.append(
                        f"{insumo.nombre}: error de conversión - {e}"
                    )
                    continue
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
                    observacion=f"Plato: {plato.nombre} x{cantidad}",
                    origen='COMANDA',
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

        self.linea_comanda_repo.guardar_lote(platos_a_crear)
        # self.movimiento_insumo_repo.guardar_lote(movimientos)
        from inventario.models import MovimientoInsumo
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

    @transaction.atomic
    def fusionar(self, comanda_id: int, otra_comanda_id: int) -> Comanda:
        comanda = self.comanda_repo.obtener_con_bloqueo(comanda_id)
        otra = self.comanda_repo.obtener_con_bloqueo(otra_comanda_id)

        if comanda.estado in ('COBRADA', 'ANULADA'):
            raise ComandaNoDisponible('La comanda principal no está activa')
        if otra.estado in ('COBRADA', 'ANULADA'):
            raise ComandaNoDisponible('La comanda a fusionar no está activa')

        from pedidos.models import LineaComanda
        LineaComanda.objects.filter(comanda_id=otra.id).update(comanda_id=comanda.id)
        otra.estado = 'ANULADA'
        otra.fecha_cierre = timezone.now()
        otra.save(update_fields=['estado', 'fecha_cierre'])
        return comanda

    @transaction.atomic
    def anular(self, comanda_id: int, usuario=None) -> Comanda:
        comanda = self.comanda_repo.obtener_con_bloqueo(comanda_id)
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
                try:
                    cantidad_a_restaurar = convertir_unidad(
                        cantidad, receta.unidad, insumo.unidad
                    )
                except (ValueError, KeyError):
                    continue
                stock_anterior = insumo.stock_actual
                insumo.stock_actual += cantidad_a_restaurar
                insumo.save(update_fields=['stock_actual'])
                movimientos.append(MovimientoInsumo(
                    insumo=insumo, comanda=comanda,
                    tipo='REPOSICION', cantidad=cantidad_a_restaurar,
                    stock_anterior=stock_anterior,
                    stock_posterior=insumo.stock_actual,
                    usuario=usuario,
                    observacion=f"Anulación comanda #{comanda.id}",
                    origen='COMANDA',
                ))

        # self.movimiento_insumo_repo.guardar_lote(movimientos)
        from inventario.models import MovimientoInsumo
        MovimientoInsumo.objects.bulk_create(movimientos)
        comanda.estado = 'ANULADA'
        comanda.fecha_cierre = timezone.now()
        comanda.save(update_fields=['estado', 'fecha_cierre'])

        _liberar_mesas(comanda)
        _notificar_plano()
        _notificar_comanda(comanda.id)
        return comanda

    @transaction.atomic
    def pagar(self, comanda_id: int, metodo: str, monto, vuelto=0,
              referencia='', caja=None) -> Comanda:
        comanda = self.comanda_repo.obtener_con_bloqueo(comanda_id)
        if comanda.estado != 'LISTA':
            raise ComandaNoDisponible('La comanda no está lista para pagar')

        monto = Decimal(str(monto))
        if monto < comanda.total - Decimal('0.01'):
            raise MontoInvalido(
                f'El monto recibido ({monto}) es menor al total ({comanda.total})'
            )

        if metodo == 'TARJETA':
            _validar_referencia_tarjeta(referencia)

        from caja.models import Pago
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

    @transaction.atomic
    def pagar_split(self, comanda_id: int, pagos_lista: list, caja=None) -> Comanda:
        comanda = self.comanda_repo.obtener_con_bloqueo(comanda_id)
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
            from caja.models import Pago
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

    def obtener_datos_tomar_pedido(self, mesa_id: int):
        from infraestructura.container import get_container
        from pedidos.models import Comanda
        from mesas.models import Mesa
        from menu.models import Categoria
        mesa = self.mesa_repo.obtener_por_id(mesa_id)
        if not mesa:
            raise RecursoNoEncontrado('Mesa no encontrada')
        comanda = Comanda.objects.filter(
            mesa=mesa, estado__in=['ABIERTA', 'EN_PREPARACION', 'LISTA']
        ).prefetch_related('lineas__plato').first()
        categorias = get_container().categoria_service.categoria_repo.listar_con_platos()
        return {'mesa': mesa, 'comanda': comanda, 'categorias': categorias}


class LineaComandaService:
    """Lógica de líneas de comanda (KDS)."""

    def __init__(self, linea_comanda_repo: ILineaComandaRepository):
        self.linea_comanda_repo = linea_comanda_repo

    @transaction.atomic
    def enviar_cocina(self, linea_id: int) -> LineaComanda:
        linea = self.linea_comanda_repo.obtener_con_bloqueo(linea_id)
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
       

    @transaction.atomic
    def marcar_listo(self, linea_id: int) -> LineaComanda:
        linea = self.linea_comanda_repo.obtener_con_bloqueo(linea_id)
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
    from infraestructura.container import get_container
    container = get_container()
    mesa = comanda.mesa
    union = get_container().union_mesa_service.repo.obtener_por_mesa(mesa.id) if hasattr(get_container().union_mesa_service, 'repo') else None
    if not union:
        from mesas.models import UnionMesa
        union = UnionMesa.objects.filter(mesas=mesa.id, activo=True).first()
    for r in Reserva.objects.filter(mesa=mesa, activo=True):
        container.reserva_service.finalizar(r.id)
    if union:
        for r in Reserva.objects.filter(union_mesa=union, activo=True):
            container.reserva_service.finalizar(r.id)


def _actualizar_estado_mesa_post_pago(comanda):
    mesa = comanda.mesa
    union = UnionMesa.objects.prefetch_related(
        'mesas__reservas', 'reservas'
    ).filter(mesas=mesa, activo=True).first()
    
    tiene_reserva = mesa.reservas.filter(activo=True).exists()
    tiene_reserva_union = union.reservas.filter(activo=True).exists() if union else False
    
    mesa.estado = 'RESERVADA' if (tiene_reserva or tiene_reserva_union) else 'LIMPIEZA'
    mesa.save(update_fields=['estado'])
    
    if union:
        # Pre-cargar las mesas de la union con sus reservas
        mesas_union = list(union.mesas.all())
        for m in mesas_union:
            if m.id != mesa.id:
                # Usar python en memoria gracias al prefetch_related
                tiene_r = any(r.activo for r in m.reservas.all()) or tiene_reserva_union
                m.estado = 'RESERVADA' if tiene_r else 'LIMPIEZA'
                m.save(update_fields=['estado'])


def _liberar_mesas(comanda):
    from infraestructura.container import get_container
    mesa = comanda.mesa
    union = get_container().union_mesa_service.repo.obtener_por_mesa(mesa.id) if hasattr(get_container().union_mesa_service, 'repo') else None
    if not union:
        from mesas.models import UnionMesa
        union = UnionMesa.objects.filter(mesas=mesa.id, activo=True).first()
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

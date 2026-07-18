from datetime import datetime, timezone
from decimal import Decimal
from django.db import transaction

from core.excepciones import (
    MesaConComandaActiva, CajaNoAbierta, RecursoNoEncontrado,
    StockInsuficiente, TransicionEstadoInvalida,
    ComandaNoDisponible, MontoInvalido, ReferenciaInvalida,
)
from dominio.entidades.comanda import Comanda
from dominio.entidades.linea_comanda import LineaComanda
from dominio.entidades.movimiento_insumo import MovimientoInsumo
from dominio.entidades.pago import Pago
from dominio.puertos.repositorios import (
    IComandaRepository, IMesaRepository, ILineaComandaRepository,
    IUnionMesaRepository, IReservaRepository, IPlatoRepository,
    IRecetaRepository, IInsumoRepository, IMovimientoInsumoRepository,
    IPagoRepository,
)
from dominio.puertos.notificador import (
    INotificadorPlano, INotificadorKDS, INotificadorComanda,
)
from dominio.entidades.unidad_conversion import convertir_unidad



class ComandaService:
    """Toda la lógica de negocio relacionada a comandas."""

    def __init__(self, comanda_repo: IComandaRepository,
                 mesa_repo: IMesaRepository,
                 caja_repo=None, union_mesa_repo=None,
                 reserva_repo=None, reserva_service=None,
                 linea_comanda_repo=None, pago_repo=None,
                 plato_repo=None, receta_repo=None,
                 insumo_repo=None, movimiento_insumo_repo=None,
                 categoria_repo=None,
                 notificador_plano: INotificadorPlano = None,
                 notificador_kds: INotificadorKDS = None,
                 notificador_comanda: INotificadorComanda = None):
        self.comanda_repo = comanda_repo
        self.mesa_repo = mesa_repo
        self.caja_repo = caja_repo
        self.union_mesa_repo = union_mesa_repo
        self.reserva_repo = reserva_repo
        self.reserva_service = reserva_service
        self.linea_comanda_repo = linea_comanda_repo
        self.pago_repo = pago_repo
        self.plato_repo = plato_repo
        self.receta_repo = receta_repo
        self.insumo_repo = insumo_repo
        self.movimiento_insumo_repo = movimiento_insumo_repo
        self.categoria_repo = categoria_repo
        self.notificador_plano = notificador_plano
        self.notificador_kds = notificador_kds
        self.notificador_comanda = notificador_comanda

    def obtener_por_id(self, comanda_id: int):
        return self.comanda_repo.obtener_por_id(comanda_id)

    def listar(self):
        return self.comanda_repo.listar()

    def listar_para_kds(self):
        return self.comanda_repo.listar_para_kds()

    @transaction.atomic
    def abrir(self, mesa_id: int, usuario) -> 'Comanda':
        caja_abierta = self.caja_repo.existe_abierta()
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

        union = self.union_mesa_repo.obtener_por_mesa(mesa.id)
        if union:
            for m_id in union.mesa_ids:
                if m_id == mesa.id:
                    continue
                comandas_m = self.comanda_repo.listar_por_mesa(m_id)
                comanda_m = next((c for c in comandas_m if c.estado in ['ABIERTA', 'EN_PREPARACION', 'LISTA']), None)
                if comanda_m:
                    return self.comanda_repo.obtener_por_id(comanda_m.id)
                m_obj = self.mesa_repo.obtener_por_id(m_id)
                if m_obj and m_obj.estado not in ['LIBRE', 'RESERVADA']:
                    raise MesaConComandaActiva(
                        f'La mesa {m_obj.numero} de la unión no está libre ni reservada'
                    )

        comanda = self.comanda_repo.guardar(Comanda(id=None, mesa_id=mesa.id, mozo_id=usuario.id, estado='ABIERTA', total=0))
        mesa.estado = 'OCUPADA'
        self.mesa_repo.guardar(mesa)

        if union:
            for m_id in union.mesa_ids:
                if m_id != mesa.id:
                    m_obj = self.mesa_repo.obtener_por_id(m_id)
                    if m_obj:
                        m_obj.estado = 'OCUPADA'
                        self.mesa_repo.guardar(m_obj)

        if self.notificador_plano:
            self.notificador_plano.notificar_refresh()
        return comanda

    @transaction.atomic
    def agregar_platos(self, comanda_id: int, platos_data: list, usuario=None) -> list:
        comanda = self.comanda_repo.obtener_con_bloqueo(comanda_id)
        if comanda.estado not in ('ABIERTA', 'LISTA'):
            raise ComandaNoDisponible('La comanda no está abierta')
        errores = []
        lineas_a_crear = []
        movimientos = []

        for item in platos_data:
            plato_id = item.get('plato_id')
            cantidad = item.get('cantidad', 1)
            observacion = item.get('observacion', '')

            plato = self.plato_repo.obtener_por_id(plato_id)
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

            todos_ri = self.receta_repo.listar_receta_insumos()
            recetas_plato = [ri for ri in todos_ri if ri.receta_id == plato.receta_id and ri.activo]
            faltantes = []
            deducciones = []

            for ri in recetas_plato:
                insumo = self.insumo_repo.obtener_por_id(ri.insumo_id)
                if not insumo:
                    faltantes.append(f"Insumo ID {ri.insumo_id}: no encontrado")
                    continue
                necesario_en_unidad_receta = ri.cantidad_por_porcion * Decimal(str(cantidad))
                try:
                    necesario = convertir_unidad(
                        necesario_en_unidad_receta,
                        ri.unidad,
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
                self.insumo_repo.guardar(insumo)

                deducciones.append(MovimientoInsumo(
                    id=None, insumo_id=insumo.id, comanda_id=comanda.id,
                    tipo='DEDUCCION', cantidad=necesario,
                    stock_anterior=stock_anterior,
                    stock_posterior=insumo.stock_actual,
                    usuario_id=getattr(usuario, 'id', None),
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
            lineas_a_crear.append(LineaComanda(
                id=None, comanda_id=comanda.id, plato_id=plato.id,
                cantidad=cantidad, observacion=observacion,
            ))

        if errores:
            raise StockInsuficiente({'errores': errores})

        self.linea_comanda_repo.guardar_lote(lineas_a_crear)
        self.movimiento_insumo_repo.guardar_lote(movimientos)

        # --- Regla InsumoAgotado ---
        insumos_agotados = set()
        for mov in movimientos:
            if mov.stock_posterior <= 0:
                insumos_agotados.add(mov.insumo_id)

        if insumos_agotados:
            todos_ri = self.receta_repo.listar_receta_insumos()
            recetas_agotadas = {
                ri.receta_id for ri in todos_ri
                if ri.insumo_id in insumos_agotados and ri.activo
            }
            if recetas_agotadas:
                for linea in lineas_a_crear:
                    plato = self.plato_repo.obtener_por_id(linea.plato_id)
                    if plato and plato.receta_id in recetas_agotadas:
                        plato.disponible = False
                        self.plato_repo.guardar(plato)

        if self.notificador_comanda:
            self.notificador_comanda.notificar_comanda(comanda.id)
        return lineas_a_crear

    @transaction.atomic
    def fusionar(self, comanda_id: int, otra_comanda_id: int):
        comanda = self.comanda_repo.obtener_con_bloqueo(comanda_id)
        otra = self.comanda_repo.obtener_con_bloqueo(otra_comanda_id)

        if comanda.estado in ('COBRADA', 'ANULADA'):
            raise ComandaNoDisponible('La comanda principal no está activa')
        if otra.estado in ('COBRADA', 'ANULADA'):
            raise ComandaNoDisponible('La comanda a fusionar no está activa')

        self.linea_comanda_repo.cambiar_comanda_lote(otra.id, comanda.id)
        otra.estado = 'ANULADA'
        otra.fecha_cierre = datetime.now(timezone.utc)
        self.comanda_repo.guardar(otra)
        return comanda

    @transaction.atomic
    def anular(self, comanda_id: int, usuario=None):
        comanda = self.comanda_repo.obtener_con_bloqueo(comanda_id)
        if comanda.estado == 'COBRADA':
            raise ComandaNoDisponible('No se puede anular una comanda ya cobrada')
        if comanda.estado == 'ANULADA':
            raise ComandaNoDisponible('La comanda ya está anulada')

        lineas = self.linea_comanda_repo.listar_por_comanda(comanda.id)
        movimientos = []
        for linea in lineas:
            plato = self.plato_repo.obtener_por_id(linea.plato_id)
            if not plato or not plato.receta_id:
                continue
            todos_ri = self.receta_repo.listar_receta_insumos()
            recetas_plato = [ri for ri in todos_ri if ri.receta_id == plato.receta_id and ri.activo]
            for ri in recetas_plato:
                insumo = self.insumo_repo.obtener_por_id(ri.insumo_id)
                if not insumo:
                    continue
                cantidad = ri.cantidad_por_porcion * Decimal(str(linea.cantidad))
                try:
                    cantidad_a_restaurar = convertir_unidad(
                        cantidad, ri.unidad, insumo.unidad
                    )
                except (ValueError, KeyError):
                    continue
                stock_anterior = insumo.stock_actual
                insumo.stock_actual += cantidad_a_restaurar
                self.insumo_repo.guardar(insumo)
                movimientos.append(MovimientoInsumo(
                    insumo_id=insumo.id, comanda_id=comanda.id,
                    tipo='REPOSICION', cantidad=cantidad_a_restaurar,
                    stock_anterior=stock_anterior,
                    stock_posterior=insumo.stock_actual,
                    usuario_id=getattr(usuario, 'id', None),
                    observacion=f"Anulación comanda #{comanda.id}",
                    origen='COMANDA',
                ))

        self.movimiento_insumo_repo.guardar_lote(movimientos)
        comanda.estado = 'ANULADA'
        comanda.fecha_cierre = datetime.now(timezone.utc)
        self.comanda_repo.guardar(comanda)

        _liberar_mesas(comanda,
                        mesa_repo=self.mesa_repo,
                        union_mesa_repo=self.union_mesa_repo,
                        reserva_repo=self.reserva_repo)
        if self.notificador_plano:
            self.notificador_plano.notificar_refresh()
        if self.notificador_comanda:
            self.notificador_comanda.notificar_comanda(comanda.id)
        return comanda

    @transaction.atomic
    def pagar(self, comanda_id: int, metodo: str, monto, vuelto=0,
              referencia='', caja=None):
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

        self.pago_repo.guardar(Pago(
            id=None, comanda_id=comanda.id, metodo=metodo,
            monto=monto, vuelto=vuelto, referencia=referencia, caja_id=caja.id
        ))
        comanda.estado = 'COBRADA'
        comanda.fecha_cierre = datetime.now(timezone.utc)
        self.comanda_repo.guardar(comanda)

        _finalizar_reservas_comanda(comanda,
                                    union_mesa_repo=self.union_mesa_repo,
                                    reserva_repo=self.reserva_repo,
                                    reserva_service=self.reserva_service)
        _actualizar_estado_mesa_post_pago(comanda,
                                          mesa_repo=self.mesa_repo,
                                          union_mesa_repo=self.union_mesa_repo,
                                          reserva_repo=self.reserva_repo)
        if self.notificador_plano:
            self.notificador_plano.notificar_refresh()
        if self.notificador_comanda:
            self.notificador_comanda.notificar_comanda(comanda.id)
        return comanda

    @transaction.atomic
    def pagar_split(self, comanda_id: int, pagos_lista: list, caja=None):
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
            self.pago_repo.guardar(Pago(id=None, comanda_id=comanda.id, metodo=pd['metodo'], monto=pd['monto'], vuelto=pd.get('vuelto', 0), referencia=pd.get('referencia', ''), caja_id=caja.id))

        comanda.estado = 'COBRADA'
        comanda.fecha_cierre = datetime.now(timezone.utc)
        self.comanda_repo.guardar(comanda)

        _finalizar_reservas_comanda(comanda,
                                    union_mesa_repo=self.union_mesa_repo,
                                    reserva_repo=self.reserva_repo,
                                    reserva_service=self.reserva_service)
        _actualizar_estado_mesa_post_pago(comanda,
                                          mesa_repo=self.mesa_repo,
                                          union_mesa_repo=self.union_mesa_repo,
                                          reserva_repo=self.reserva_repo)
        if self.notificador_plano:
            self.notificador_plano.notificar_refresh()
        if self.notificador_comanda:
            self.notificador_comanda.notificar_comanda(comanda.id)
        return comanda

    def obtener_datos_tomar_pedido(self, mesa_id: int):
        mesa = self.mesa_repo.obtener_por_id(mesa_id)
        if not mesa:
            raise RecursoNoEncontrado('Mesa no encontrada')
        comandas = self.comanda_repo.listar_por_mesa(mesa.id)
        comanda = next((c for c in comandas if c.estado in ['ABIERTA', 'EN_PREPARACION', 'LISTA']), None)
        categorias = self.categoria_repo.listar_con_platos()
        return {'mesa': mesa, 'comanda': comanda, 'categorias': categorias}


class LineaComandaService:
    """Lógica de líneas de comanda (KDS)."""

    def __init__(self, linea_comanda_repo: ILineaComandaRepository,
                 comanda_repo: IComandaRepository = None,
                 notificador_plano: INotificadorPlano = None,
                 notificador_kds: INotificadorKDS = None):
        self.linea_comanda_repo = linea_comanda_repo
        self.comanda_repo = comanda_repo
        self.notificador_plano = notificador_plano
        self.notificador_kds = notificador_kds

    def listar(self):
        return self.linea_comanda_repo.listar()

    def obtener_por_id(self, linea_id: int):
        return self.linea_comanda_repo.obtener_por_id(linea_id)

    @transaction.atomic
    def enviar_cocina(self, linea_id: int):
        linea = self.linea_comanda_repo.obtener_con_bloqueo(linea_id)
        if linea.estado != 'PENDIENTE':
            raise TransicionEstadoInvalida(
                'Solo se puede enviar a cocina en estado PENDIENTE'
            )
        linea.estado = 'EN_PREP'
        self.linea_comanda_repo.guardar(linea)

        # Verificar si todas las líneas están en preparación
        lineas = self.linea_comanda_repo.listar_por_comanda(linea.comanda_id)
        if all(l.estado == 'EN_PREP' for l in lineas):
            comanda = self.comanda_repo.obtener_por_id(linea.comanda_id)
            if comanda:
                comanda.estado = 'EN_PREPARACION'
                self.comanda_repo.guardar(comanda)

        if self.notificador_kds:
            self.notificador_kds.notificar_refresh()
        return linea
       

    @transaction.atomic
    def marcar_listo(self, linea_id: int):
        linea = self.linea_comanda_repo.obtener_con_bloqueo(linea_id)
        if linea.estado != 'EN_PREP':
            raise TransicionEstadoInvalida(
                'Solo se puede marcar LISTO una línea EN_PREPARACION'
            )
        linea.estado = 'LISTO'
        self.linea_comanda_repo.guardar(linea)

        # Verificar si todas las líneas están listas
        lineas = self.linea_comanda_repo.listar_por_comanda(linea.comanda_id)
        if all(l.estado == 'LISTO' for l in lineas):
            comanda = self.comanda_repo.obtener_por_id(linea.comanda_id)
            if comanda:
                comanda.estado = 'LISTA'
                self.comanda_repo.guardar(comanda)

        if self.notificador_kds:
            self.notificador_kds.notificar_refresh()
        if self.notificador_plano:
            self.notificador_plano.notificar_refresh()
        return linea

    def obtener_panel_kds(self):
        """Retorna comandas activas para el panel de cocina (KDS)."""
        return self.comanda_repo.listar_para_kds()

    @staticmethod
    def obtener_comandas_con_lineas_pendientes():
        """Retorna IDs de comandas que tienen líneas PENDIENTE o EN_PREP."""
        return []


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


def _finalizar_reservas_comanda(comanda, union_mesa_repo=None,
                                reserva_repo=None, reserva_service=None):
    mesa_id = comanda.mesa_id
    union = union_mesa_repo.obtener_por_mesa(mesa_id)
    for r in reserva_repo.listar_activas_por_mesa(mesa_id):
        reserva_service.finalizar(r.id)
    if union:
        for r in reserva_repo.listar_activas_por_union(union.id):
            reserva_service.finalizar(r.id)


def _actualizar_estado_mesa_post_pago(comanda, mesa_repo=None,
                                      union_mesa_repo=None,
                                      reserva_repo=None):
    mesa_id = comanda.mesa_id
    mesa = mesa_repo.obtener_por_id(mesa_id)
    if not mesa:
        return
    union = union_mesa_repo.obtener_por_mesa(mesa_id)
    
    tiene_reserva = bool(reserva_repo.listar_activas_por_mesa(mesa_id))
    tiene_reserva_union = bool(reserva_repo.listar_activas_por_union(union.id)) if union else False
    
    mesa.estado = 'RESERVADA' if (tiene_reserva or tiene_reserva_union) else 'LIMPIEZA'
    mesa_repo.guardar(mesa)
    
    if union:
        for m_id in union.mesa_ids:
            if m_id != mesa_id:
                m = mesa_repo.obtener_por_id(m_id)
                if m:
                    tiene_r = bool(reserva_repo.listar_activas_por_mesa(m_id)) or tiene_reserva_union
                    m.estado = 'RESERVADA' if tiene_r else 'LIMPIEZA'
                    mesa_repo.guardar(m)


def _liberar_mesas(comanda, mesa_repo=None, union_mesa_repo=None,
                    reserva_repo=None):
    mesa_id = comanda.mesa_id
    mesa = mesa_repo.obtener_por_id(mesa_id)
    if not mesa:
        return
    union = union_mesa_repo.obtener_por_mesa(mesa_id)
    mesas_a_liberar_ids = [mesa_id]
    if union:
        mesas_a_liberar_ids = list(union.mesa_ids)
    for m_id in mesas_a_liberar_ids:
        m = mesa_repo.obtener_por_id(m_id)
        if not m:
            continue
        tiene_reserva = bool(reserva_repo.listar_activas_por_mesa(m_id))
        if union:
            tiene_reserva = tiene_reserva or bool(reserva_repo.listar_activas_por_union(union.id))
        m.estado = 'RESERVADA' if tiene_reserva else 'LIBRE'
        mesa_repo.guardar(m)

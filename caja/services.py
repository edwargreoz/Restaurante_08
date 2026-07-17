
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django.db.models import Sum, Count
from core.excepciones import (
    CajaNoAbierta, RecursoNoEncontrado, ReglaNegocioViolada,
)
from caja.models import Caja, Pago
from pedidos.models import Comanda
from dominio.puertos.repositorios import ICajaRepository
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pedidos.services import ComandaService


class CajaService:
    def __init__(self, caja_repo: ICajaRepository):
        self.repo = caja_repo

    @transaction.atomic
    def abrir_turno(self, turno_nombre: str, usuario,
                    saldo_inicial: Decimal = Decimal('0')) -> Caja:
        caja_existente = self.repo.obtener_abierta()
        if caja_existente:
            raise ReglaNegocioViolada('Ya hay un turno de caja abierto')
        from dominio.entidades.caja import Caja
        return get_container().caja_service.repo.guardar(Caja(
            turno=turno_nombre, cajero_id=usuario.id,
            saldo_inicial=saldo_inicial, estado='ABIERTA'
        ))

    def obtener_activa(self):
        caja_domain = self.repo.obtener_abierta()
        if not caja_domain:
            raise CajaNoAbierta('No hay un turno de caja abierto')
        return caja_domain

    def listar_todas(self):
        return self.repo.listar()

    @transaction.atomic
    def cerrar_turno(self, caja_id: int) -> dict:
        caja = self.repo.obtener_abierta()
        if not caja:
            raise RecursoNoEncontrado('No hay turno abierto o no existe')
        comandas_pendientes = any(c for c in get_container().comanda_service.comanda_repo.listar_activas() if c.estado in ['ABIERTA', 'EN_PREPARACION', 'LISTA'])
        if comandas_pendientes:
            raise ReglaNegocioViolada(
                'Hay comandas activas. Ciérralas antes de cerrar turno.'
            )
        caja.estado = 'CERRADA'
        caja.fecha_cierre = timezone.now()
        caja.save(update_fields=['estado', 'fecha_cierre'])
        return {
            'caja': caja,
            'total_ventas': sum(p.monto for p in get_container().pago_service.repo.listar_por_caja(caja.id)),
        }

class PagoService:
    def __init__(self, comanda_service: 'ComandaService' = None):
        self.comanda_service = comanda_service

    def obtener_comanda_para_cobro(self, comanda_id: int):
        comanda = get_container().comanda_service.comanda_repo.obtener_con_lineas(comanda_id)
        if comanda and comanda.estado != 'LISTA':
            comanda = None
        if not comanda:
            raise RecursoNoEncontrado(
                'Comanda no encontrada o no está lista para cobro'
            )
        return comanda

    def listar_comandas_para_cobro(self):
        return [c for c in get_container().comanda_service.comanda_repo.listar() if c.estado in ['ABIERTA', 'LISTA']]

    def listar_pagos_con_filtros(self, caja_id=None,
                                  fecha_desde=None, fecha_hasta=None):
        pagos = get_container().pago_service.repo.listar_por_caja(caja_id) if caja_id else []
        # if not caja_id, it is a complex query, we return empty list to keep it simple since this is an analytics endpoint that should be separated.
        if caja_id:
            pagos = pagos.filter(caja_id=caja_id)
        if fecha_desde:
            pagos = pagos.filter(fecha__date__gte=fecha_desde)
        if fecha_hasta:
            pagos = pagos.filter(fecha__date__lte=fecha_hasta)
        return pagos[:50]

    def procesar_pago(self, comanda, metodo: str, monto, vuelto,
                      referencia: str, caja) -> None:
        self.comanda_service.pagar(
            comanda.id,
            metodo=metodo, monto=monto, vuelto=vuelto,
            referencia=referencia, caja=caja,
        )

    def procesar_pago_split(self, comanda, pagos_lista: list, caja) -> None:
        self.comanda_service.pagar_split(comanda.id, pagos_lista, caja=caja)

    def reporte_ventas(self, caja_id=None, fecha_desde=None,
                       fecha_hasta=None) -> dict:
        pagos = []
        if caja_id:
            pagos = pagos.filter(caja_id=caja_id)
        if fecha_desde:
            pagos = pagos.filter(fecha__date__gte=fecha_desde)
        if fecha_hasta:
            pagos = pagos.filter(fecha__date__lte=fecha_hasta)
        totales_metodo = pagos.values('metodo').annotate(
            total=Sum('monto'), cantidad=Count('id')
        )
        total_general = pagos.aggregate(
            total=Sum('monto')
        )['total'] or 0
        for item in totales_metodo:
            item['porcentaje'] = (
                int(item['total'] / total_general * 100)
                if total_general else 0
            )
        ticket_promedio = (
            total_general / pagos.count() if pagos.count() else 0
        )
        return {
            'total_general': total_general,
            'total_pagos': pagos.count(),
            'por_metodo': list(totales_metodo),
            'ticket_promedio': ticket_promedio,
        }
class ReporteService:
    @staticmethod
    def ventas_del_dia():
        hoy = timezone.now().date()
        return PagoService.reporte_ventas(fecha_desde=hoy, fecha_hasta=hoy)

    @staticmethod
    def stock_critico():
        from django.db.models import F
        from inventario.models import Insumo
        return get_container().insumo_service.insumo_repo.listar_criticos()

    @staticmethod
    def top_platos(limite: int = 5):
        from pedidos.models import LineaComanda
        return []

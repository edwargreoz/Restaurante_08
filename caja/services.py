
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

class CajaService:
    def __init__(self, caja_repo: ICajaRepository):
        self.repo = caja_repo

    @transaction.atomic
    def abrir_turno(self, turno_nombre: str, usuario,
                    saldo_inicial: Decimal = Decimal('0')) -> Caja:
        caja_existente = Caja.objects.select_for_update().filter(
            estado='ABIERTA'
        ).first()
        if caja_existente:
            raise ReglaNegocioViolada('Ya hay un turno de caja abierto')
        return Caja.objects.create(
            turno=turno_nombre, cajero=usuario,
            saldo_inicial=saldo_inicial,
        )

    def obtener_activa(self):
        caja_domain = self.repo.obtener_abierta()
        if not caja_domain:
            raise CajaNoAbierta('No hay un turno de caja abierto')
        return Caja.objects.filter(estado='ABIERTA').first()

    def listar_todas(self):
        return Caja.objects.all()

    @transaction.atomic
    def cerrar_turno(self, caja_id: int) -> dict:
        caja = Caja.objects.select_for_update().filter(
            id=caja_id, estado='ABIERTA'
        ).first()
        if not caja:
            raise RecursoNoEncontrado('No hay turno abierto o no existe')
        comandas_pendientes = Comanda.objects.filter(
            estado__in=['ABIERTA', 'EN_PREPARACION', 'LISTA']
        ).exists()
        if comandas_pendientes:
            raise ReglaNegocioViolada(
                'Hay comandas activas. Ciérralas antes de cerrar turno.'
            )
        caja.estado = 'CERRADA'
        caja.fecha_cierre = timezone.now()
        caja.save(update_fields=['estado', 'fecha_cierre'])
        return {
            'caja': caja,
            'total_ventas': Pago.objects.filter(caja=caja).aggregate(
                total=Sum('monto')
            )['total'] or 0,
        }

class PagoService:
    @staticmethod
    def obtener_comanda_para_cobro(comanda_id: int):
        comanda = Comanda.objects.prefetch_related(
            'lineas__plato', 'pagos'
        ).filter(id=comanda_id, estado='LISTA').first()
        if not comanda:
            raise RecursoNoEncontrado(
                'Comanda no encontrada o no está lista para cobro'
            )
        return comanda

    @staticmethod
    def listar_comandas_para_cobro():
        return Comanda.objects.filter(
            estado__in=['ABIERTA', 'LISTA']
        ).select_related('mesa', 'mozo').order_by('-fecha_apertura')

    @staticmethod
    def listar_pagos_con_filtros(caja_id=None,
                                  fecha_desde=None, fecha_hasta=None):
        pagos = Pago.objects.select_related(
            'comanda__mesa', 'comanda__mozo', 'caja'
        ).all()
        if caja_id:
            pagos = pagos.filter(caja_id=caja_id)
        if fecha_desde:
            pagos = pagos.filter(fecha__date__gte=fecha_desde)
        if fecha_hasta:
            pagos = pagos.filter(fecha__date__lte=fecha_hasta)
        return pagos[:50]

    @staticmethod
    def procesar_pago(comanda, metodo: str, monto, vuelto,
                      referencia: str, caja) -> None:
        from pedidos.services import ComandaService
        from infraestructura.container import get_container
        container = get_container()
        svc = ComandaService(
            comanda_repo=container.comanda_repo,
            mesa_repo=container.mesa_repo,
        )
        svc.pagar(
            comanda.id,
            metodo=metodo, monto=monto, vuelto=vuelto,
            referencia=referencia, caja=caja,
        )

    @staticmethod
    def procesar_pago_split(comanda, pagos_lista: list, caja) -> None:
        from pedidos.services import ComandaService
        from infraestructura.container import get_container
        container = get_container()
        svc = ComandaService(
            comanda_repo=container.comanda_repo,
            mesa_repo=container.mesa_repo,
        )
        svc.pagar_split(comanda.id, pagos_lista, caja=caja)

    @staticmethod
    def reporte_ventas(caja_id=None, fecha_desde=None,
                       fecha_hasta=None) -> dict:
        pagos = Pago.objects.all()
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
        return Insumo.objects.filter(
            stock_actual__lt=F('stock_minimo')
        ).order_by('stock_actual')

    @staticmethod
    def top_platos(limite: int = 5):
        from pedidos.models import LineaComanda
        return LineaComanda.objects.values(
            'plato__nombre'
        ).annotate(
            total=Sum('cantidad')
        ).order_by('-total')[:limite]

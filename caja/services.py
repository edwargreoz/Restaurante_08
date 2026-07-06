
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django.db.models import Sum, Count, Q, F
from core.excepciones import (
    CajaNoAbierta, RecursoNoEncontrado, MontoInvalido,
    ReferenciaInvalida, ReglaNegocioViolada,
)
from caja.models import Caja, Pago
from pedidos.models import Comanda


class CajaService:
    @staticmethod
    @transaction.atomic
    def abrir_turno(turno_nombre: str, usuario,
                    saldo_inicial: Decimal = Decimal('0')) -> Caja:
        caja_existente = Caja.objects.filter(estado='ABIERTA').first()
        if caja_existente:
            raise ReglaNegocioViolada('Ya hay un turno de caja abierto')
        return Caja.objects.create(
            turno=turno_nombre, cajero=usuario,
            saldo_inicial=saldo_inicial,
        )

    @staticmethod
    def listar_todas():
        return Caja.objects.all()

    @staticmethod
    @transaction.atomic
    def cerrar_turno(caja_id: int) -> dict:
        caja = Caja.objects.filter(id=caja_id, estado='ABIERTA').first()
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
                total=Sum('monto'))['total'] or 0,
        }


class PagoService:
    @staticmethod
    def procesar_pago(comanda, metodo: str, monto, vuelto,
                       referencia: str, caja) -> None:
        from django.core.exceptions import ValidationError
        try:
            comanda.pagar(
                metodo=metodo, monto=monto, vuelto=vuelto,
                referencia=referencia, caja=caja,
            )
        except ValidationError as e:
            raise ReglaNegocioViolada(str(e))

    @staticmethod
    def procesar_pago_split(comanda, pagos_lista: list, caja) -> None:
        from django.core.exceptions import ValidationError
        try:
            comanda.pagar_split(pagos_lista, caja=caja)
        except ValidationError as e:
            if hasattr(e, 'message_dict'):
                msgs = [str(m) for sub in e.message_dict.values() for m in sub]
                raise ReglaNegocioViolada('; '.join(msgs))
            raise ReglaNegocioViolada(str(e))
    @staticmethod
    def reporte_ventas(caja_id=None, fecha_desde=None, fecha_hasta=None) -> dict:
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
        total_general = pagos.aggregate(total=Sum('monto'))['total'] or 0
        for item in totales_metodo:
            item['porcentaje'] = int(item['total'] / total_general * 100) if total_general else 0
        ticket_promedio = total_general / pagos.count() if pagos.count() else 0
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

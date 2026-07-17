
from collections import defaultdict
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from dominio.entidades.caja import Caja
from dominio.puertos.repositorios import (
    ICajaRepository, IComandaRepository, IPagoRepository,
)
from pedidos.models import LineaComanda
from core.excepciones import (
    CajaNoAbierta, RecursoNoEncontrado, ReglaNegocioViolada,
)
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pedidos.services import ComandaService



class CajaService:
    def __init__(self, caja_repo: ICajaRepository,
                 comanda_repo: IComandaRepository = None,
                 pago_repo: IPagoRepository = None):
        self.repo = caja_repo
        self.comanda_repo = comanda_repo
        self.pago_repo = pago_repo

    @transaction.atomic
    def abrir_turno(self, turno_nombre: str, usuario,
                    saldo_inicial: Decimal = Decimal('0')):
        caja_existente = self.repo.obtener_abierta()
        if caja_existente:
            raise ReglaNegocioViolada('Ya hay un turno de caja abierto')
        return self.repo.guardar(Caja(
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
        comandas_pendientes = any(c for c in self.comanda_repo.listar_activas() if c.estado in ['ABIERTA', 'EN_PREPARACION', 'LISTA'])
        if comandas_pendientes:
            raise ReglaNegocioViolada(
                'Hay comandas activas. Ciérralas antes de cerrar turno.'
            )
        caja.estado = 'CERRADA'
        caja.fecha_cierre = timezone.now()
        self.repo.guardar(caja)
        return {
            'caja': caja,
            'total_ventas': sum(p.monto for p in self.pago_repo.listar_por_caja(caja.id)),
        }

class PagoService:
    def __init__(self, comanda_service: 'ComandaService' = None,
                 comanda_repo: IComandaRepository = None,
                 pago_repo: IPagoRepository = None):
        self.comanda_service = comanda_service
        self.comanda_repo = comanda_repo
        self.pago_repo = pago_repo

    def obtener_comanda_para_cobro(self, comanda_id: int):
        comanda = self.comanda_repo.obtener_con_lineas(comanda_id)
        if comanda and comanda.estado != 'LISTA':
            comanda = None
        if not comanda:
            raise RecursoNoEncontrado(
                'Comanda no encontrada o no está lista para cobro'
            )
        return comanda

    def listar_comandas_para_cobro(self):
        return [c for c in self.comanda_repo.listar() if c.estado in ['ABIERTA', 'LISTA']]

    def listar_pagos_con_filtros(self, caja_id=None,
                                  fecha_desde=None, fecha_hasta=None):
        pagos = self.pago_repo.listar_por_caja(caja_id) if caja_id else []
        # if not caja_id, it is a complex query, we return empty list to keep it simple since this is an analytics endpoint that should be separated.
        if caja_id:
            pagos = [p for p in pagos if p.caja_id == caja_id]
        if fecha_desde:
            pagos = [p for p in pagos if getattr(p, 'fecha', None) and p.fecha.date() >= fecha_desde]
        if fecha_hasta:
            pagos = [p for p in pagos if getattr(p, 'fecha', None) and p.fecha.date() <= fecha_hasta]
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
        pagos = self.pago_repo.listar_por_caja(caja_id) if caja_id else self.pago_repo.listar()
        if caja_id:
            pagos = [p for p in pagos if p.caja_id == caja_id]
        if fecha_desde:
            pagos = [p for p in pagos if getattr(p, 'fecha', None) and p.fecha.date() >= fecha_desde]
        if fecha_hasta:
            pagos = [p for p in pagos if getattr(p, 'fecha', None) and p.fecha.date() <= fecha_hasta]
        resumen = defaultdict(lambda: {'total': 0, 'cantidad': 0})
        total_general = 0
        for p in pagos:
            resumen[p.metodo]['total'] += p.monto
            resumen[p.metodo]['cantidad'] += 1
            total_general += p.monto
        
        totales_metodo = [{'metodo': k, 'total': v['total'], 'cantidad': v['cantidad']} for k, v in resumen.items()]
        for item in totales_metodo:
            item['porcentaje'] = (
                int(item['total'] / total_general * 100)
                if total_general else 0
            )
        ticket_promedio = (
            total_general / len(pagos) if len(pagos) else 0
        )
        return {
            'total_general': total_general,
            'total_pagos': len(pagos),
            'por_metodo': list(totales_metodo),
            'ticket_promedio': ticket_promedio,
        }
class ReporteService:
    def __init__(self, pago_service: PagoService = None,
                 insumo_repo=None, linea_comanda_repo=None):
        self.pago_service = pago_service
        self.insumo_repo = insumo_repo
        self.linea_comanda_repo = linea_comanda_repo

    def ventas_del_dia(self):
        hoy = timezone.now().date()
        return self.pago_service.reporte_ventas(fecha_desde=hoy, fecha_hasta=hoy)

    def stock_critico(self):
        return self.insumo_repo.listar_criticos()

    def top_platos(self, limite: int = 5):
        from collections import defaultdict
        from dominio.puertos.repositorios import IPlatoRepository
        lineas = self.linea_comanda_repo.listar()
        vendidos = defaultdict(lambda: {'cantidad': 0, 'plato_id': None})
        for linea in lineas:
            plato_id = linea.plato_id
            vendidos[plato_id]['cantidad'] += linea.cantidad
            vendidos[plato_id]['plato_id'] = plato_id
        ranking = sorted(vendidos.values(), key=lambda x: x['cantidad'], reverse=True)[:limite]
        return ranking

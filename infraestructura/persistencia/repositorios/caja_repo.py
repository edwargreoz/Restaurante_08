
from typing import Optional, List
from caja.models import Caja as CajaModel
from dominio.entidades.caja import Caja


class CajaRepository:
    def obtener_abierta(self) -> Optional[Caja]:
        c = CajaModel.objects.select_related('cajero').filter(estado='ABIERTA').first()
        if not c:
            return None
        nombre = ''
        if c.cajero:
            nombre = c.cajero.get_full_name() or c.cajero.username
        return Caja(id=c.id, turno=c.turno, cajero_id=c.cajero_id,
                    saldo_inicial=c.saldo_inicial, estado=c.estado,
                    nombre_cajero=nombre)

    def existe_abierta(self) -> bool:
        return CajaModel.objects.filter(estado='ABIERTA').exists()

    def guardar(self, caja: Caja) -> Caja:
        obj, _ = CajaModel.objects.update_or_create(
            id=caja.id,
            defaults={
                'turno': caja.turno, 'cajero_id': caja.cajero_id,
                'saldo_inicial': caja.saldo_inicial, 'estado': caja.estado,
            }
        )
        return Caja(id=obj.id, turno=obj.turno, cajero_id=obj.cajero_id,
                    saldo_inicial=obj.saldo_inicial, estado=obj.estado,
                    nombre_cajero=caja.nombre_cajero)

    def listar(self) -> List[Caja]:
        return [
            Caja(id=c.id, turno=c.turno, cajero_id=c.cajero_id,
                 saldo_inicial=c.saldo_inicial, estado=c.estado,
                 nombre_cajero=c.cajero.get_full_name() or c.cajero.username if c.cajero else '')
            for c in CajaModel.objects.select_related('cajero').all()
        ]

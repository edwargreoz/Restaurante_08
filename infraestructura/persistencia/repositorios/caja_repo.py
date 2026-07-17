
from typing import Optional, List
from caja.models import Caja as CajaModel
from dominio.entidades.caja import Caja

class CajaRepository:
    def obtener_abierta(self) -> Optional[Caja]:
        c = CajaModel.objects.filter(estado='ABIERTA').first()
        if not c:
            return None
        return Caja(id=c.id, turno=c.turno, cajero_id=c.cajero_id,
                    saldo_inicial=c.saldo_inicial, estado=c.estado)
    
    def guardar(self, caja: Caja) -> Caja:
        CajaModel.objects.update_or_create(
            id=caja.id,
            defaults={
                'turno': caja.turno, 'cajero_id': caja.cajero_id,
                'saldo_inicial': caja.saldo_inicial, 'estado': caja.estado,
            }
        )
        return caja

    def listar(self) -> List[Caja]:
        return [
            Caja(id=c.id, turno=c.turno, cajero_id=c.cajero_id,
                 saldo_inicial=c.saldo_inicial, estado=c.estado)
            for c in CajaModel.objects.all()
        ]

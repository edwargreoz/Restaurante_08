
from typing import Optional
from caja.models import Caja as CajaModel
from dominio.entidades.caja import Caja


class CajaRepository:
    def obtener_activa(self) -> Optional[Caja]:
        c = CajaModel.objects.filter(estado='ABIERTA').first()
        if not c:
            return None
        return Caja(id=c.id, turno=c.turno, cajero_id=c.cajero_id,
                    saldo_inicial=c.saldo_inicial, estado=c.estado)

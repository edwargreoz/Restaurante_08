
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional


@dataclass
class Caja:
    id: Optional[int]
    turno: str
    cajero_id: int
    saldo_inicial: Decimal = Decimal('0')
    estado: str = 'ABIERTA'
    fecha_apertura: Optional[datetime] = None
    fecha_cierre: Optional[datetime] = None

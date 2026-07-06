
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional


@dataclass
class Pago:
    id: Optional[int]
    comanda_id: int
    metodo: str
    monto: Decimal
    vuelto: Decimal = Decimal('0')
    referencia: str = ''

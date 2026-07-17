from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional
from datetime import datetime

@dataclass
class MovimientoInsumo:
    id: Optional[int] = None
    insumo_id: Optional[int] = None
    insumo: Optional[any] = None
    comanda_id: Optional[int] = None
    tipo: str = ''
    cantidad: Decimal = field(default_factory=lambda: Decimal('0'))
    stock_anterior: Decimal = field(default_factory=lambda: Decimal('0'))
    stock_posterior: Decimal = field(default_factory=lambda: Decimal('0'))
    usuario_id: Optional[int] = None
    usuario: Optional[any] = None
    observacion: str = ''
    fecha: Optional[datetime] = None
    origen: str = ''
    caja_id: Optional[int] = None
    activo: bool = True

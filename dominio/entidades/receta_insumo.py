from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional

@dataclass
class RecetaInsumo:
    id: Optional[int] = None
    receta_id: Optional[int] = None
    insumo_id: Optional[int] = None
    cantidad_por_porcion: Decimal = field(default_factory=lambda: Decimal('0'))
    unidad: str = 'UNIDAD'
    activo: bool = True

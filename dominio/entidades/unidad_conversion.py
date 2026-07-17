from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional

@dataclass
class UnidadConversion:
    id: Optional[int] = None
    insumo_id: Optional[int] = None
    nombre: str = ''
    contiene_cantidad: Decimal = field(default_factory=lambda: Decimal('1'))
    contiene_unidad_id: Optional[int] = None
    contiene_unidad: Optional['UnidadConversion'] = None
    es_base: bool = False
    activo: bool = True

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional

UNIDADES_BASE = {
    'UNIDAD': ('UNIDAD', Decimal('1')),
    'KG': ('GR', Decimal('1000')),
    'GR': ('GR', Decimal('1')),
    'LT': ('ML', Decimal('1000')),
    'ML': ('ML', Decimal('1')),
}


def convertir_unidad(cantidad, de_unidad, a_unidad):
    if de_unidad == a_unidad:
        return cantidad
    if de_unidad not in UNIDADES_BASE or a_unidad not in UNIDADES_BASE:
        raise ValueError(
            f"Unidad no reconocida: {de_unidad} o {a_unidad}"
        )
    base_de, factor_de = UNIDADES_BASE[de_unidad]
    base_a, factor_a = UNIDADES_BASE[a_unidad]
    if base_de != base_a:
        raise ValueError(
            f"No se puede convertir {de_unidad} a {a_unidad}: "
            f"son categorias diferentes"
        )
    en_base = cantidad * factor_de
    return en_base / factor_a


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

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional


GRUPOS_UNIDAD = (
    ('VOLUMEN', 'Volumen'),
    ('PESO', 'Peso'),
    ('CANTIDAD', 'Cantidad'),
)


@dataclass
class UnidadCocina:
    id: Optional[int]
    nombre: str
    equivalencia_cantidad: Decimal
    equivalencia_unidad: str
    grupo: str = 'VOLUMEN'
    activo: bool = True

    def convertir_a_base(self, cantidad: Decimal) -> Decimal:
        return cantidad * self.equivalencia_cantidad

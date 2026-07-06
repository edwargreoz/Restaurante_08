
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional


@dataclass
class Plato:
    id: Optional[int]
    nombre: str
    precio: Decimal
    categoria_id: int
    receta_id: Optional[int]
    disponible: bool = True
    tiempo_preparacion_min: int = 15

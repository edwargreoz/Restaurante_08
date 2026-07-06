
from dataclasses import dataclass
from typing import Optional


@dataclass
class Categoria:
    id: Optional[int]
    nombre: str
    es_bebida: bool = False
    orden_display: int = 0

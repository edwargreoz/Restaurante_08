from dataclasses import dataclass, field
from typing import Optional, List

@dataclass
class Receta:
    id: Optional[int] = None
    nombre: str = ''
    activo: bool = True
    insumos: List[any] = field(default_factory=list)

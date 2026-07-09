from dataclasses import dataclass, field
from typing import Optional


@dataclass
class UnionMesa:
    id: Optional[int]
    mesa_ids: list = field(default_factory=list)
    activa: bool = True

from dataclasses import dataclass, field
from typing import Optional, List
from core.excepciones import UnionInvalida


@dataclass
class UnionMesa:
    id: Optional[int]
    mesa_ids: list = field(default_factory=list)
    activo: bool = True

    def validar_minimo_mesas(self) -> None:
        if len(self.mesa_ids) < 2:
            raise UnionInvalida('Una unión necesita al menos 2 mesas')

    def contiene_mesa(self, mesa_id: int) -> bool:
        return mesa_id in self.mesa_ids

    def desactivar(self) -> None:
        self.activo = False

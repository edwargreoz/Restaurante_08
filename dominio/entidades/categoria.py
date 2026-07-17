
from dataclasses import dataclass
from typing import Optional
from core.excepciones import ReglaNegocioViolada


@dataclass
class Categoria:
    id: Optional[int]
    nombre: str
    es_bebida: bool = False
    orden_display: int = 0

    def validar_nombre(self) -> None:
        if not self.nombre or not self.nombre.strip():
            raise ReglaNegocioViolada('El nombre de la categoría no puede estar vacío')
        if len(self.nombre.strip()) < 2:
            raise ReglaNegocioViolada('El nombre de la categoría debe tener al menos 2 caracteres')

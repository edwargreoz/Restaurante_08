
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional
from dominio.excepciones import ReglaNegocioViolada, PlatoNoDisponible


@dataclass
class Plato:
    id: Optional[int]
    nombre: str
    precio: Decimal
    categoria_id: int
    receta_id: Optional[int]
    disponible: bool = True
    tiempo_preparacion_min: int = 15
    descripcion: str = ''
    receta_nombre: Optional[str] = None

    def marcar_no_disponible(self) -> None:
        self.disponible = False

    def marcar_disponible(self) -> None:
        self.disponible = True

    def validar_disponible(self) -> None:
        if not self.disponible:
            raise PlatoNoDisponible(f'El plato "{self.nombre}" no está disponible')

    def tiene_receta(self) -> bool:
        return self.receta_id is not None

    def validar_precio(self) -> None:
        if self.precio <= 0:
            raise ReglaNegocioViolada(f'El precio de "{self.nombre}" debe ser mayor a 0')

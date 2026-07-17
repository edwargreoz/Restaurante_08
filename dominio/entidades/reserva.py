from dataclasses import dataclass
from datetime import date, time
from typing import Optional
from core.excepciones import ReglaNegocioViolada


@dataclass
class Reserva:
    id: Optional[int]
    mesa_id: Optional[int]
    union_mesa_id: Optional[int]
    cliente_nombre: str
    fecha: date
    hora_inicio: time
    hora_fin: time
    num_personas: int
    activo: bool = True
    finalizada: bool = False

    def cancelar(self) -> None:
        if not self.activo:
            raise ReglaNegocioViolada('Esta reserva ya está cancelada')
        self.activo = False

    def finalizar(self) -> None:
        if not self.activo:
            raise ReglaNegocioViolada('Esta reserva ya no está activa')
        self.activo = False
        self.finalizada = True

    def esta_activa(self) -> bool:
        return self.activo and not self.finalizada

    def es_para_mesa_individual(self) -> bool:
        return self.mesa_id is not None

    def es_para_union(self) -> bool:
        return self.union_mesa_id is not None

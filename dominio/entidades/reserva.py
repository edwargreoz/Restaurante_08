from dataclasses import dataclass
from datetime import date, time
from typing import Optional
from dominio.excepciones import ReglaNegocioViolada


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

    def validar_horario(self) -> None:
        if self.hora_inicio >= self.hora_fin:
            raise ReglaNegocioViolada('La hora de inicio debe ser anterior a la hora de fin')
        hora_apertura = time(8, 0)
        hora_cierre = time(23, 0)
        if self.hora_inicio < hora_apertura or self.hora_fin > hora_cierre:
            raise ReglaNegocioViolada(f'El horario de reserva debe ser entre {hora_apertura} y {hora_cierre}')

    def validar_capacidad(self) -> None:
        if self.num_personas <= 0:
            raise ReglaNegocioViolada('El número de personas debe ser mayor a 0')
        if self.num_personas > 20:
            raise ReglaNegocioViolada('El número de personas no puede exceder 20')

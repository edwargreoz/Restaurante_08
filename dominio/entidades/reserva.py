from dataclasses import dataclass
from datetime import date, time
from typing import Optional


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

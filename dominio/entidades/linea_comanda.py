from dataclasses import dataclass
from typing import Optional
from core.excepciones import TransicionEstadoInvalida


@dataclass
class LineaComanda:
    id: Optional[int]
    comanda_id: int
    plato_id: int
    cantidad: int = 1
    observacion: str = ''
    estado: str = 'PENDIENTE'

    TRANSICIONES = {
        'PENDIENTE': ['EN_PREP', 'ENTREGADO'],
        'EN_PREP': ['LISTO'],
        'LISTO': ['ENTREGADO'],
        'ENTREGADO': [],
    }

    def cambiar_estado(self, nuevo_estado: str) -> None:
        if nuevo_estado not in self.TRANSICIONES.get(self.estado, []):
            raise TransicionEstadoInvalida(
                f'No se puede cambiar línea de {self.estado} a {nuevo_estado}'
            )
        self.estado = nuevo_estado

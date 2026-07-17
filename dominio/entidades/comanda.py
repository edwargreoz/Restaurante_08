from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional
from core.excepciones import TransicionEstadoInvalida


@dataclass
class Comanda:
    id: Optional[int]
    mesa_id: int
    mozo_id: int
    estado: str = 'ABIERTA'
    fecha_apertura: Optional[datetime] = None
    fecha_cierre: Optional[datetime] = None
    total: Decimal = Decimal('0')

    TRANSICIONES = {
        'ABIERTA': ['EN_PREPARACION', 'ANULADA'],
        'EN_PREPARACION': ['LISTA', 'ANULADA'],
        'LISTA': ['COBRADA'],
        'COBRADA': [],
        'ANULADA': [],
    }

    def cambiar_estado(self, nuevo_estado: str) -> None:
        if nuevo_estado not in self.TRANSICIONES.get(self.estado, []):
            raise TransicionEstadoInvalida(
                f'No se puede cambiar de {self.estado} a {nuevo_estado}'
            )
        self.estado = nuevo_estado

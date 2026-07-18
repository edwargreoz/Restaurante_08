from dataclasses import dataclass
from decimal import Decimal
from typing import Optional
from dominio.excepciones import TransicionEstadoInvalida


@dataclass
class LineaComanda:
    id: Optional[int]
    comanda_id: int
    plato_id: int
    cantidad: int = 1
    observacion: str = ''
    estado: str = 'PENDIENTE'
    nombre_plato: Optional[str] = None
    precio_unitario: Optional[Decimal] = None
    tiempo_preparacion_min: Optional[int] = None

    @property
    def subtotal(self) -> Decimal:
        if self.precio_unitario is not None:
            return self.precio_unitario * self.cantidad
        return Decimal('0')

    TRANSICIONES = {
        'PENDIENTE': ['EN_PREP'],
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

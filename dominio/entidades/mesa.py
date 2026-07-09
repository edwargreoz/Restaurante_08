from dataclasses import dataclass
from typing import Optional
from core.excepciones import ReglaNegocioViolada


@dataclass
class Mesa:
    id: Optional[int]
    numero: int
    capacidad: int
    zona: str = 'SALON'
    estado: str = 'LIBRE'

    ZONAS_VALIDAS = ('SALON', 'TERRAZA', 'VIP')
    ESTADOS_VALIDOS = ('LIBRE', 'OCUPADA', 'RESERVADA', 'LIMPIEZA')

    def ocupar(self):
        if self.estado not in ('LIBRE', 'RESERVADA'):
            raise ReglaNegocioViolada(f'Mesa {self.numero} no está disponible')
        self.estado = 'OCUPADA'

    def liberar(self):
        self.estado = 'LIBRE'

    def limpiar(self):
        self.estado = 'LIMPIEZA'

    def reservar(self):
        self.estado = 'RESERVADA'

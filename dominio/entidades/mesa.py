from dataclasses import dataclass
from typing import Optional
from dominio.excepciones import ReglaNegocioViolada


@dataclass
class Mesa:
    id: Optional[int]
    numero: int
    capacidad: int
    zona: str = 'SALON'
    estado: str = 'LIBRE'
    activo: bool = True

    ZONAS_VALIDAS = ('SALON', 'TERRAZA', 'VIP')
    ESTADOS_VALIDOS = ('LIBRE', 'OCUPADA', 'RESERVADA', 'LIMPIEZA')

    def ocupar(self):
        if self.estado not in ('LIBRE', 'RESERVADA'):
            raise ReglaNegocioViolada(f'Mesa {self.numero} no está disponible')
        self.estado = 'OCUPADA'

    def liberar(self):
        if self.estado != 'OCUPADA':
            raise ReglaNegocioViolada(f'Mesa {self.numero} no se puede liberar desde estado {self.estado}')
        self.estado = 'LIBRE'

    def limpiar(self):
        if self.estado != 'OCUPADA':
            raise ReglaNegocioViolada(f'Mesa {self.numero} no se puede limpiar desde estado {self.estado}')
        self.estado = 'LIMPIEZA'

    def reservar(self):
        if self.estado != 'LIBRE':
            raise ReglaNegocioViolada(f'Mesa {self.numero} no se puede reservar desde estado {self.estado}')
        self.estado = 'RESERVADA'

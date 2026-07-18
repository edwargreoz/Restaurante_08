
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional
from dominio.excepciones import ReglaNegocioViolada, TransicionEstadoInvalida


@dataclass
class Caja:
    id: Optional[int]
    turno: str
    cajero_id: int
    saldo_inicial: Decimal = Decimal('0')
    estado: str = 'ABIERTA'
    fecha_apertura: Optional[datetime] = None
    fecha_cierre: Optional[datetime] = None
    nombre_cajero: str = ''

    ESTADOS_VALIDOS = ('ABIERTA', 'CERRADA')

    def esta_abierta(self) -> bool:
        return self.estado == 'ABIERTA'

    def cerrar(self) -> None:
        if self.estado != 'ABIERTA':
            raise TransicionEstadoInvalida('La caja ya está cerrada')
        self.estado = 'CERRADA'
        self.fecha_cierre = datetime.now()

    def validar_saldo_inicial(self) -> None:
        if self.saldo_inicial < 0:
            raise ReglaNegocioViolada('El saldo inicial no puede ser negativo')


from dataclasses import dataclass
from decimal import Decimal
from typing import Optional
from core.excepciones import MontoInvalido, ReferenciaInvalida


@dataclass
class Pago:
    id: Optional[int]
    comanda_id: int
    metodo: str
    monto: Decimal
    vuelto: Decimal = Decimal('0')
    referencia: str = ''
    caja_id: Optional[int] = None

    METODOS_VALIDOS = ('EFECTIVO', 'TARJETA', 'YAPE', 'PLIN', 'TRANSFERENCIA')

    def calcular_vuelto(self, total_comanda: Decimal) -> Decimal:
        if self.monto < total_comanda:
            raise MontoInvalido(
                f'El monto ({self.monto}) es menor al total ({total_comanda})'
            )
        self.vuelto = self.monto - total_comanda
        return self.vuelto

    def validar_referencia_tarjeta(self) -> None:
        if self.metodo == 'TARJETA':
            digitos = ''.join(c for c in self.referencia if c.isdigit())
            if len(digitos) < 4:
                raise ReferenciaInvalida(
                    'Para pagos con tarjeta ingresa los últimos 4 dígitos'
                )

    def validar_metodo(self) -> None:
        if self.metodo not in self.METODOS_VALIDOS:
            raise MontoInvalido(f'Método de pago "{self.metodo}" no válido')

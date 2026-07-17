
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional
from core.excepciones import StockInsuficiente


@dataclass
class Insumo:
    id: Optional[int]
    nombre: str
    unidad: str
    stock_actual: Decimal = Decimal('0')
    stock_minimo: Decimal = Decimal('0')
    costo_unitario: Decimal = Decimal('0')

    @property
    def stock_critico(self) -> bool:
        return self.stock_actual < self.stock_minimo

    def deducir_stock(self, cantidad: Decimal) -> None:
        if self.stock_actual < cantidad:
            raise StockInsuficiente(f'Stock insuficiente de {self.nombre}')
        self.stock_actual -= cantidad

    def reponer_stock(self, cantidad: Decimal) -> None:
        self.stock_actual += cantidad

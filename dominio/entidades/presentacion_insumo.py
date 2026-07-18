from dataclasses import dataclass
from decimal import Decimal
from typing import Optional


UNIDADES_MEDIDA = (
    ('UNIDAD', 'Unidad'),
    ('KG', 'Kilogramo'),
    ('GR', 'Gramo'),
    ('LT', 'Litro'),
    ('ML', 'Mililitro'),
)


@dataclass
class PresentacionInsumo:
    id: Optional[int]
    insumo_id: int
    nombre: str
    cantidad: Decimal
    unidad_medida: str
    costo_compra: Decimal = Decimal('0')
    es_principal: bool = False
    activo: bool = True

    def calcular_stock_base(self, unidades_compradas: int) -> Decimal:
        return self.cantidad * Decimal(str(unidades_compradas))

    def calcular_costo_por_unidad_base(self) -> Decimal:
        total_base = self.cantidad
        if total_base <= 0:
            return Decimal('0')
        return self.costo_compra / total_base

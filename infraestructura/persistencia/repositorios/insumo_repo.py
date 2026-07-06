
from typing import Optional, List
from inventario.models import Insumo as InsumoModel
from dominio.entidades.insumo import Insumo


class InsumoRepository:
    def obtener_por_id(self, insumo_id: int) -> Optional[Insumo]:
        try:
            m = InsumoModel.objects.get(id=insumo_id, activo=True)
            return self._a_entidad(m)
        except InsumoModel.DoesNotExist:
            return None

    def listar_criticos(self) -> List[Insumo]:
        from django.db.models import F
        return [
            self._a_entidad(m)
            for m in InsumoModel.objects.filter(stock_actual__lt=F('stock_minimo'))
        ]

    def _a_entidad(self, m) -> Insumo:
        return Insumo(
            id=m.id, nombre=m.nombre, unidad=m.unidad,
            stock_actual=m.stock_actual, stock_minimo=m.stock_minimo,
            costo_unitario=m.costo_unitario,
        )

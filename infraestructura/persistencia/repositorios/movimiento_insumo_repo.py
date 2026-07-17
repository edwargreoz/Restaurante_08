from typing import List
from inventario.models import MovimientoInsumo as MovimientoModel
from dominio.entidades.movimiento_insumo import MovimientoInsumo

class MovimientoInsumoRepository:
    def guardar_lote(self, movimientos: List[MovimientoInsumo]) -> None:
        modelos = [
            MovimientoModel(
                insumo_id=m.insumo_id, tipo=m.tipo, cantidad=m.cantidad,
                observacion=m.observacion, usuario_id=m.usuario_id
            ) for m in movimientos
        ]
        MovimientoModel.objects.bulk_create(modelos)

    def guardar(self, movimiento: MovimientoInsumo) -> MovimientoInsumo:
        m = MovimientoModel.objects.create(
            insumo_id=movimiento.insumo_id, tipo=movimiento.tipo, cantidad=movimiento.cantidad,
            observacion=movimiento.observacion, usuario_id=movimiento.usuario_id
        )
        return MovimientoInsumo(id=m.id, insumo_id=m.insumo_id, tipo=m.tipo, cantidad=m.cantidad, observacion=m.observacion, usuario_id=m.usuario_id, fecha=m.fecha)

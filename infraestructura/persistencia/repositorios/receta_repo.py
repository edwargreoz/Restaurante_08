from typing import List, Optional
from inventario.models import Receta as RecetaModel, RecetaInsumo as RecetaInsumoModel
from dominio.entidades.receta import Receta
from dominio.entidades.receta_insumo import RecetaInsumo

class RecetaRepository:
    def obtener_o_crear(self, nombre: str) -> Receta:
        r, _ = RecetaModel.objects.get_or_create(nombre=nombre)
        return Receta(id=r.id, nombre=r.nombre, descripcion=r.descripcion, instrucciones=r.instrucciones, tiempo_preparacion=r.tiempo_preparacion)

    def listar(self) -> List[Receta]:
        return [Receta(id=r.id, nombre=r.nombre, descripcion=r.descripcion, instrucciones=r.instrucciones, tiempo_preparacion=r.tiempo_preparacion) for r in RecetaModel.objects.all()]
        
    def listar_receta_insumos(self) -> List[RecetaInsumo]:
        return [RecetaInsumo(id=ri.id, receta_id=ri.receta_id, insumo_id=ri.insumo_id, cantidad=ri.cantidad, unidad_id=ri.unidad_id) for ri in RecetaInsumoModel.objects.select_related('receta', 'insumo').all()]

    def obtener_receta_insumo_o_crear(self, receta_id: int, insumo_id: int, cantidad: float, unidad_id: int) -> RecetaInsumo:
        ri, _ = RecetaInsumoModel.objects.get_or_create(receta_id=receta_id, insumo_id=insumo_id, defaults={'cantidad': cantidad, 'unidad_id': unidad_id})
        return RecetaInsumo(id=ri.id, receta_id=ri.receta_id, insumo_id=ri.insumo_id, cantidad=ri.cantidad, unidad_id=ri.unidad_id)

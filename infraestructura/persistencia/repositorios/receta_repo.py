from typing import List, Optional
from inventario.models import Receta as RecetaModel, RecetaInsumo as RecetaInsumoModel
from dominio.entidades.receta import Receta
from dominio.entidades.receta_insumo import RecetaInsumo


class RecetaRepository:

    def _a_entidad(self, r) -> Receta:
        return Receta(id=r.id, nombre=r.nombre, activo=r.activo)

    def _a_entidad_ri(self, ri) -> RecetaInsumo:
        return RecetaInsumo(
            id=ri.id, receta_id=ri.receta_id, insumo_id=ri.insumo_id,
            cantidad_por_porcion=ri.cantidad_por_porcion,
            unidad=ri.unidad, activo=ri.activo,
        )

    def obtener_o_crear(self, nombre: str) -> Receta:
        r, _ = RecetaModel.objects.get_or_create(nombre=nombre)
        return self._a_entidad(r)

    def listar(self) -> List[Receta]:
        return [self._a_entidad(r) for r in RecetaModel.objects.all()]

    def listar_receta_insumos(self) -> List[RecetaInsumo]:
        return [
            self._a_entidad_ri(ri)
            for ri in RecetaInsumoModel.objects.select_related('receta', 'insumo').all()
        ]

    def obtener_receta_insumo_o_crear(self, receta_id: int, insumo_id: int,
                                      cantidad_por_porcion, unidad: str) -> RecetaInsumo:
        ri, _ = RecetaInsumoModel.objects.get_or_create(
            receta_id=receta_id, insumo_id=insumo_id,
            defaults={'cantidad_por_porcion': cantidad_por_porcion, 'unidad': unidad},
        )
        return self._a_entidad_ri(ri)

    def obtener_receta_insumo(self, receta_insumo_id: int) -> Optional[RecetaInsumo]:
        try:
            ri = RecetaInsumoModel.objects.get(id=receta_insumo_id)
            return self._a_entidad_ri(ri)
        except RecetaInsumoModel.DoesNotExist:
            return None

    def eliminar_receta_insumo(self, ri_id: int) -> None:
        RecetaInsumoModel.objects.filter(id=ri_id).delete()

    def actualizar_receta_insumo(self, ri_id: int, **kwargs) -> RecetaInsumo:
        RecetaInsumoModel.objects.filter(id=ri_id).update(**kwargs)
        ri = RecetaInsumoModel.objects.get(id=ri_id)
        return self._a_entidad_ri(ri)

    def guardar(self, receta) -> Receta:
        r, _ = RecetaModel.objects.update_or_create(
            id=receta.id,
            defaults={'nombre': receta.nombre, 'activo': getattr(receta, 'activo', True)}
        )
        return self._a_entidad(r)

    def eliminar(self, receta_id: int) -> None:
        RecetaModel.objects.filter(id=receta_id).delete()

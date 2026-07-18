from typing import Optional, List
from inventario.models import PresentacionInsumo as PresentacionModel
from dominio.entidades.presentacion_insumo import PresentacionInsumo


class PresentacionInsumoRepository:

    def obtener_por_id(self, presentacion_id: int) -> Optional[PresentacionInsumo]:
        try:
            m = PresentacionModel.objects.get(id=presentacion_id)
            return self._a_entidad(m)
        except PresentacionModel.DoesNotExist:
            return None

    def guardar(self, presentacion: PresentacionInsumo) -> PresentacionInsumo:
        m, _ = PresentacionModel.objects.update_or_create(
            id=presentacion.id,
            defaults={
                'insumo_id': presentacion.insumo_id,
                'nombre': presentacion.nombre,
                'cantidad': presentacion.cantidad,
                'unidad_medida': presentacion.unidad_medida,
                'costo_compra': presentacion.costo_compra,
                'es_principal': presentacion.es_principal,
            }
        )
        return self._a_entidad(m)

    def listar_por_insumo(self, insumo_id: int) -> List[PresentacionInsumo]:
        return [
            self._a_entidad(m)
            for m in PresentacionModel.objects.filter(insumo_id=insumo_id)
        ]

    def listar_catalogo(self) -> List[PresentacionInsumo]:
        return [
            self._a_entidad(m)
            for m in PresentacionModel.objects.filter(insumo_id__isnull=True)
        ]

    def eliminar(self, presentacion_id: int) -> None:
        PresentacionModel.objects.filter(id=presentacion_id).delete()

    def _a_entidad(self, m) -> PresentacionInsumo:
        return PresentacionInsumo(
            id=m.id, insumo_id=m.insumo_id, nombre=m.nombre,
            cantidad=m.cantidad, unidad_medida=m.unidad_medida,
            costo_compra=m.costo_compra, es_principal=m.es_principal,
        )

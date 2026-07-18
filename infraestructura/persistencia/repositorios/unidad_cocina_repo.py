from typing import Optional, List
from inventario.models import UnidadCocina as UnidadCocinaModel
from dominio.entidades.unidad_cocina import UnidadCocina


class UnidadCocinaRepository:

    def obtener_por_id(self, unidad_id: int) -> Optional[UnidadCocina]:
        try:
            m = UnidadCocinaModel.objects.get(id=unidad_id)
            return self._a_entidad(m)
        except UnidadCocinaModel.DoesNotExist:
            return None

    def guardar(self, unidad: UnidadCocina) -> UnidadCocina:
        m, _ = UnidadCocinaModel.objects.update_or_create(
            id=unidad.id,
            defaults={
                'nombre': unidad.nombre,
                'equivalencia_cantidad': unidad.equivalencia_cantidad,
                'equivalencia_unidad': unidad.equivalencia_unidad,
                'grupo': unidad.grupo,
            }
        )
        return self._a_entidad(m)

    def listar(self) -> List[UnidadCocina]:
        return [
            self._a_entidad(m)
            for m in UnidadCocinaModel.objects.all()
        ]

    def eliminar(self, unidad_id: int) -> None:
        UnidadCocinaModel.objects.filter(id=unidad_id).delete()

    def _a_entidad(self, m) -> UnidadCocina:
        return UnidadCocina(
            id=m.id, nombre=m.nombre,
            equivalencia_cantidad=m.equivalencia_cantidad,
            equivalencia_unidad=m.equivalencia_unidad,
            grupo=m.grupo,
        )

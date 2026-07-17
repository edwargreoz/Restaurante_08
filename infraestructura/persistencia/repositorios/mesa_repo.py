from typing import Optional, List
from mesas.models import Mesa as MesaModel
from dominio.entidades.mesa import Mesa


class MesaRepository:

    def obtener_con_bloqueo(self, mesa_id: int) -> Optional[Mesa]:
        try:
            m = MesaModel.activos.select_for_update().get(id=mesa_id)
            return self._a_entidad(m)
        except MesaModel.DoesNotExist:
            return None

    def obtener_por_id(self, mesa_id: int) -> Optional[Mesa]:
        try:
            m = MesaModel.activos.select_related().get(id=mesa_id)
            return self._a_entidad(m)
        except MesaModel.DoesNotExist:
            return None

    def obtener_con_union(self, mesa_id: int) -> Optional[Mesa]:
        try:
            m = MesaModel.activos.prefetch_related(
                'uniones_mesa'
            ).select_related().get(id=mesa_id)
            return m
        except MesaModel.DoesNotExist:
            return None

    def guardar(self, mesa: Mesa) -> Mesa:
        m, _ = MesaModel.objects.update_or_create(
            id=mesa.id,
            defaults={'numero': mesa.numero, 'capacidad': mesa.capacidad,
                      'zona': mesa.zona, 'estado': mesa.estado}
        )
        return self._a_entidad(m)

    def listar_activas(self) -> List[Mesa]:
        return [self._a_entidad(m) for m in MesaModel.activos.order_by('numero')]

    def listar_por_zona(self, zona: str) -> List[Mesa]:
        return [self._a_entidad(m) for m in MesaModel.activos.filter(
            zona=zona
        ).order_by('numero')]

    def _a_entidad(self, m) -> Mesa:
        return Mesa(id=m.id, numero=m.numero, capacidad=m.capacidad,
                    zona=m.zona, estado=m.estado)

from typing import Optional
from mesas.models import Mesa as MesaModel
from dominio.entidades.mesa import Mesa


class MesaRepository:
    def obtener_por_id(self, mesa_id: int) -> Optional[Mesa]:
        try:
            m = MesaModel.activos.get(id=mesa_id)
            return Mesa(id=m.id, numero=m.numero, capacidad=m.capacidad,
                        zona=m.zona, estado=m.estado)
        except MesaModel.DoesNotExist:
            return None

    def guardar(self, mesa: Mesa) -> Mesa:
        m, _ = MesaModel.objects.update_or_create(
            id=mesa.id,
            defaults={'numero': mesa.numero, 'capacidad': mesa.capacidad,
                      'zona': mesa.zona, 'estado': mesa.estado}
        )
        return Mesa(id=m.id, numero=m.numero, capacidad=m.capacidad,
                    zona=m.zona, estado=m.estado)

    def listar_activas(self):
        return [self._a_entidad(m) for m in MesaModel.activos.all()]

    def _a_entidad(self, m):
        return Mesa(id=m.id, numero=m.numero, capacidad=m.capacidad,
                    zona=m.zona, estado=m.estado)

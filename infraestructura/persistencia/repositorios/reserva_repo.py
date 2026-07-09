from typing import Optional
from reservas.models import Reserva as ReservaModel
from dominio.entidades.reserva import Reserva


class ReservaRepository:
    def obtener_por_id(self, reserva_id: int) -> Optional[Reserva]:
        try:
            r = ReservaModel.objects.get(id=reserva_id)
            return self._a_entidad(r)
        except ReservaModel.DoesNotExist:
            return None

    def _a_entidad(self, r):
        return Reserva(
            id=r.id, mesa_id=r.mesa_id, union_mesa_id=r.union_mesa_id,
            cliente_nombre=r.cliente_nombre, fecha=r.fecha,
            hora_inicio=r.hora_inicio, hora_fin=r.hora_fin,
            num_personas=r.num_personas, activa=r.activa, finalizada=r.finalizada,
        )

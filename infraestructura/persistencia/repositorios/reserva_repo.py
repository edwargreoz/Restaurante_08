from typing import Optional, List
from reservas.models import Reserva as ReservaModel
from dominio.entidades.reserva import Reserva


class ReservaRepository:
    def obtener_por_id(self, reserva_id: int) -> Optional[Reserva]:
        try:
            r = ReservaModel.objects.select_related(
                'mesa', 'union_mesa', 'creado_por'
            ).get(id=reserva_id)
            return self._a_entidad(r)
        except ReservaModel.DoesNotExist:
            return None

    def guardar(self, reserva: Reserva) -> Reserva:
        r, _ = ReservaModel.objects.update_or_create(
            id=reserva.id,
            defaults={
                'mesa_id': reserva.mesa_id, 'union_mesa_id': reserva.union_mesa_id,
                'cliente_nombre': reserva.cliente_nombre, 'fecha': reserva.fecha,
                'hora_inicio': reserva.hora_inicio, 'hora_fin': reserva.hora_fin,
                'num_personas': reserva.num_personas, 'activo': reserva.activo,
                'finalizada': reserva.finalizada,
            }
        )
        return self._a_entidad(r)

    def listar(self) -> List[Reserva]:
        return [self._a_entidad(r) for r in ReservaModel.activos.select_related(
            'mesa', 'union_mesa', 'creado_por'
        ).prefetch_related('union_mesa__mesas').all()]

    def eliminar(self, reserva_id: int) -> None:
        ReservaModel.objects.filter(id=reserva_id).update(activo=False)

    def _a_entidad(self, r) -> Reserva:
        return Reserva(
            id=r.id, mesa_id=r.mesa_id, union_mesa_id=r.union_mesa_id,
            cliente_nombre=r.cliente_nombre, fecha=r.fecha,
            hora_inicio=r.hora_inicio, hora_fin=r.hora_fin,
            num_personas=r.num_personas, activo=r.activo, finalizada=r.finalizada,
        )

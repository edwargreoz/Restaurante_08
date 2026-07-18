from typing import Optional, List
from reservas.models import Reserva as ReservaModel
from dominio.entidades.reserva import Reserva


class ReservaRepository:

    def obtener_con_bloqueo(self, reserva_id: int) -> Optional[Reserva]:
        try:
            m = ReservaModel.objects.select_for_update().get(id=reserva_id)
            return self._a_entidad(m)
        except ReservaModel.DoesNotExist:
            return None

    def obtener_por_id(self, reserva_id: int) -> Optional[Reserva]:
        try:
            r = ReservaModel.activos.select_related(
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
                'cliente_contacto': reserva.cliente_contacto,
                'observacion': reserva.observacion,
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
        mesa_numero = None
        if r.mesa:
            mesa_numero = r.mesa.numero
        union_mesa_nombre = None
        if r.union_mesa:
            mesas_nums = list(r.union_mesa.mesas.values_list('numero', flat=True)) if hasattr(r.union_mesa, 'mesas') else []
            union_mesa_nombre = ' + '.join(f'Mesa {m}' for m in mesas_nums) if mesas_nums else None
        creado_por_nombre = ''
        if hasattr(r, 'creado_por') and r.creado_por:
            creado_por_nombre = r.creado_por.get_full_name() or r.creado_por.username
        return Reserva(
            id=r.id, mesa_id=r.mesa_id, union_mesa_id=r.union_mesa_id,
            cliente_nombre=r.cliente_nombre, fecha=r.fecha,
            hora_inicio=r.hora_inicio, hora_fin=r.hora_fin,
            num_personas=r.num_personas, activo=r.activo, finalizada=r.finalizada,
            cliente_contacto=getattr(r, 'cliente_contacto', ''),
            observacion=getattr(r, 'observacion', ''),
            creado_por_nombre=creado_por_nombre,
            mesa_numero=mesa_numero,
            union_mesa_nombre=union_mesa_nombre,
        )

    def listar_activas_por_mesa(self, mesa_id: int) -> List[Reserva]:
        return [self._a_entidad(r) for r in ReservaModel.activos.filter(mesa_id=mesa_id, activo=True)]
        
    def listar_activas_por_union(self, union_id: int) -> List[Reserva]:
        return [self._a_entidad(r) for r in ReservaModel.activos.filter(union_mesa_id=union_id, activo=True)]

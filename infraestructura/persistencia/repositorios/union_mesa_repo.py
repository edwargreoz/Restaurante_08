from typing import Optional, List
from mesas.models import UnionMesa as UnionMesaModel
from dominio.entidades.union_mesa import UnionMesa


class UnionMesaRepository:

    def guardar(self, union: UnionMesa) -> UnionMesa:
        u, _ = UnionMesaModel.objects.update_or_create(
            id=union.id, defaults={'activo': union.activo}
        )
        if union.mesa_ids:
            u.mesas.set(union.mesa_ids)
        return self._a_entidad(u)

    def obtener_activa_por_mesa(self, mesa_id: int) -> Optional[UnionMesa]:
        u = UnionMesaModel.objects.filter(mesas=mesa_id, activo=True).first()
        return self._a_entidad(u) if u else None

    def obtener_por_mesa(self, mesa_id: int) -> Optional[UnionMesa]:
        u = UnionMesaModel.objects.filter(mesas=mesa_id, activo=True).first()
        return self._a_entidad(u) if u else None

    def obtener_por_id(self, union_id: int) -> Optional[UnionMesa]:
        u = UnionMesaModel.objects.filter(id=union_id, activo=True).first()
        return self._a_entidad(u) if u else None

    def listar_activas(self) -> List[UnionMesa]:
        return [self._a_entidad(u) for u in UnionMesaModel.objects.filter(activo=True)]

    def _a_entidad(self, u) -> UnionMesa:
        mesas_qs = u.mesas.all()
        mesa_ids = [m.id for m in mesas_qs] if u.id else []
        capacidad_total = sum(m.capacidad for m in mesas_qs) if u.id else 0
        return UnionMesa(
            id=u.id,
            mesa_ids=mesa_ids,
            activo=u.activo,
            capacidad_total=capacidad_total,
        )

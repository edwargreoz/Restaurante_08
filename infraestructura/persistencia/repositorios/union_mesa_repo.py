from typing import Optional
from mesas.models import UnionMesa as UnionMesaModel
from dominio.entidades.union_mesa import UnionMesa

class UnionMesaRepository:
    def guardar(self, union: UnionMesa) -> UnionMesa:
        u, _ = UnionMesaModel.objects.update_or_create(id=union.id, defaults={'activo': union.activo})
        if hasattr(union, 'mesas') and union.mesas:
            u.mesas.set(union.mesas)
        return self._a_entidad(u)
        
    def obtener_activa_por_mesa(self, mesa_id: int) -> Optional[UnionMesa]:
        u = UnionMesaModel.objects.filter(mesas=mesa_id, activo=True).first()
        return self._a_entidad(u) if u else None
        
    def obtener_por_mesa(self, mesa_id: int) -> Optional[UnionMesa]:
        u = UnionMesaModel.objects.filter(mesas=mesa_id, activo=True).first()
        return self._a_entidad(u) if u else None

    def _a_entidad(self, u) -> UnionMesa:
        ent = UnionMesa(id=u.id, activo=u.activo)
        ent.mesas = [m.id for m in u.mesas.all()] if u.id else []
        return ent

    def obtener_por_id(self, union_id: int) -> Optional[UnionMesa]:
        u = UnionMesaModel.objects.filter(id=union_id, activo=True).first()
        return self._a_entidad(u) if u else None

    def listar_activas(self):
        return [self._a_entidad(u) for u in UnionMesaModel.objects.filter(activo=True)]

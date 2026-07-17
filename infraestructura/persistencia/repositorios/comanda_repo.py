from typing import Optional, List
from django.db.models import Q
from pedidos.models import Comanda as ComandaModel
from dominio.entidades.comanda import Comanda


class ComandaRepository:
    """Adaptador Django ORM para el repositorio de comandas."""

    def obtener_por_id(self, comanda_id: int) -> Optional[Comanda]:
        try:
            modelo = ComandaModel.objects.select_related(
                'mesa', 'mozo'
            ).get(id=comanda_id, activo=True)
            return self._modelo_a_entidad(modelo)
        except ComandaModel.DoesNotExist:
            return None

    def obtener_con_lineas(self, comanda_id: int) -> Optional[Comanda]:
        try:
            modelo = ComandaModel.objects.select_related(
                'mesa', 'mozo'
            ).prefetch_related('lineas__plato').get(
                id=comanda_id, activo=True
            )
            return modelo
        except ComandaModel.DoesNotExist:
            return None

    def guardar(self, comanda: Comanda) -> Comanda:
        modelo, _ = ComandaModel.objects.update_or_create(
            id=comanda.id,
            defaults={
                'mesa_id': comanda.mesa_id,
                'mozo_id': comanda.mozo_id,
                'estado': comanda.estado,
            }
        )
        return self._modelo_a_entidad(modelo)

    def listar(self) -> List[Comanda]:
        return [
            self._modelo_a_entidad(m)
            for m in ComandaModel.objects.select_related(
                'mesa', 'mozo'
            ).order_by('-fecha_apertura')
        ]

    def listar_activas(self) -> List[Comanda]:
        return [
            self._modelo_a_entidad(m)
            for m in ComandaModel.activos.select_related(
                'mesa', 'mozo'
            ).filter(
                estado__in=['ABIERTA', 'EN_PREPARACION', 'LISTA']
            )
        ]

    def listar_por_mesa(self, mesa_id: int) -> List[Comanda]:
        return [
            self._modelo_a_entidad(m)
            for m in ComandaModel.activos.select_related(
                'mesa', 'mozo'
            ).filter(mesa_id=mesa_id)
        ]

    def listar_para_kds(self) -> List[Comanda]:
        comanda_ids = ComandaModel.activos.filter(
            lineas__estado__in=['PENDIENTE', 'EN_PREP']
        ).values_list('id', flat=True).distinct()
        return [
            self._modelo_a_entidad(m)
            for m in ComandaModel.objects.filter(
                Q(estado='EN_PREPARACION') | Q(id__in=comanda_ids)
            ).select_related(
                'mesa', 'mozo'
            ).prefetch_related(
                'lineas__plato'
            ).order_by('fecha_apertura')
        ]

    def _modelo_a_entidad(self, modelo) -> Comanda:
        return Comanda(
            id=modelo.id,
            mesa_id=modelo.mesa_id,
            mozo_id=modelo.mozo_id,
            estado=modelo.estado,
            fecha_apertura=modelo.fecha_apertura,
            fecha_cierre=modelo.fecha_cierre,
            total=modelo.total,
        )

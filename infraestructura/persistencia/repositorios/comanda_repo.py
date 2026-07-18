from typing import Optional, List
from django.db.models import Q
from pedidos.models import Comanda as ComandaModel
from dominio.entidades.comanda import Comanda


class ComandaRepository:

    def obtener_con_bloqueo(self, comanda_id: int) -> Optional[Comanda]:
        try:
            m = ComandaModel.objects.select_for_update().get(id=comanda_id)
            return self._modelo_a_entidad(m)
        except ComandaModel.DoesNotExist:
            return None

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
            return self._modelo_a_entidad(modelo)
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

    def contar_activas(self) -> int:
        return ComandaModel.activos.filter(
            estado__in=['ABIERTA', 'EN_PREPARACION']
        ).count()

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

    def listar_pendientes_por_caja(self, caja_id: int) -> List[Comanda]:
        return [
            self._modelo_a_entidad(m)
            for m in ComandaModel.activos.select_related(
                'mesa', 'mozo'
            ).filter(
                pagos__caja_id=caja_id,
                estado__in=['ABIERTA', 'EN_PREPARACION', 'LISTA']
            ).distinct()
        ]

    def _modelo_a_entidad(self, modelo) -> Comanda:
        lineas = None
        if hasattr(modelo, 'lineas'):
            from dominio.entidades.linea_comanda import LineaComanda
            lineas = [
                LineaComanda(
                    id=l.id, comanda_id=l.comanda_id, plato_id=l.plato_id,
                    cantidad=l.cantidad, observacion=l.observacion, estado=l.estado,
                    nombre_plato=l.plato.nombre if l.plato else None,
                    precio_unitario=l.plato.precio if l.plato else None,
                    tiempo_preparacion_min=l.plato.tiempo_preparacion_min if l.plato else None,
                )
                for l in modelo.lineas.all()
            ] if modelo.lineas.exists() else []
        total = modelo.total
        if not total:
            from decimal import Decimal
            total = sum(
                (l.cantidad * (l.plato.precio if l.plato else 0))
                for l in (modelo.lineas.all() if hasattr(modelo, 'lineas') else [])
            ) if hasattr(modelo, 'lineas') else Decimal('0')
        mozo_nombre = ''
        if hasattr(modelo, 'mozo') and modelo.mozo:
            mozo_nombre = modelo.mozo.get_full_name() or modelo.mozo.username
        return Comanda(
            id=modelo.id,
            mesa_id=modelo.mesa_id,
            mozo_id=modelo.mozo_id,
            estado=modelo.estado,
            fecha_apertura=modelo.fecha_apertura,
            fecha_cierre=modelo.fecha_cierre,
            total=total,
            numero_mesa=modelo.mesa.numero if hasattr(modelo, 'mesa') and modelo.mesa else None,
            nombre_mozo=mozo_nombre,
            lineas=lineas or [],
        )

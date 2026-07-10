from typing import Optional
from pedidos.models import Comanda as ComandaModel, LineaComanda as LineaComandaModel
from dominio.entidades.comanda import Comanda


class ComandaRepository:
    """Adaptador Django ORM para el repositorio de comandas."""

    def obtener_por_id(self, comanda_id: int) -> Optional[Comanda]:
        try:
            modelo = ComandaModel.objects.get(id=comanda_id, activo=True)
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

    def _modelo_a_entidad(self, modelo) -> Comanda:
        return Comanda(
            id=modelo.id,
            mesa_id=modelo.mesa_id,
            mozo_id=modelo.mozo_id,
            estado=modelo.estado,
            fecha_apertura=modelo.fecha_apertura,
            fecha_cierre=modelo.fecha_cierre,
        )

from typing import Optional, List
from pedidos.models import LineaComanda as LineaComandaModel
from dominio.entidades.linea_comanda import LineaComanda


class LineaComandaRepository:

    def obtener_con_bloqueo(self, linea_id: int) -> Optional[LineaComanda]:
        try:
            l = LineaComandaModel.objects.select_for_update().get(id=linea_id)
            return self._a_entidad(l)
        except LineaComandaModel.DoesNotExist:
            return None

    def guardar_lote(self, lineas: List[LineaComanda]) -> None:
        modelos = [LineaComandaModel(
            comanda_id=l.comanda_id, plato_id=l.plato_id,
            cantidad=l.cantidad, observacion=l.observacion, estado=l.estado
        ) for l in lineas]
        LineaComandaModel.objects.bulk_create(modelos)

    def obtener_por_id(self, linea_id: int) -> Optional[LineaComanda]:
        try:
            l = LineaComandaModel.objects.get(id=linea_id)
            return self._a_entidad(l)
        except LineaComandaModel.DoesNotExist:
            return None

    def guardar(self, linea: LineaComanda) -> LineaComanda:
        l, _ = LineaComandaModel.objects.update_or_create(
            id=linea.id,
            defaults={
                'comanda_id': linea.comanda_id, 'plato_id': linea.plato_id,
                'cantidad': linea.cantidad, 'observacion': linea.observacion,
                'estado': linea.estado,
            }
        )
        return self._a_entidad(l)

    def listar(self) -> List[LineaComanda]:
        return [self._a_entidad(l) for l in LineaComandaModel.objects.select_related(
            'plato', 'comanda'
        ).order_by('-id')]

    def listar_por_comanda(self, comanda_id: int) -> List[LineaComanda]:
        return [self._a_entidad(l) for l in LineaComandaModel.objects.select_related(
            'plato'
        ).filter(comanda_id=comanda_id)]

    def _a_entidad(self, l) -> LineaComanda:
        return LineaComanda(
            id=l.id, comanda_id=l.comanda_id, plato_id=l.plato_id,
            cantidad=l.cantidad, observacion=l.observacion, estado=l.estado,
        )

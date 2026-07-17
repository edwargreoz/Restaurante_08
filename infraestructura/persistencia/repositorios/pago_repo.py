from typing import Optional, List
from caja.models import Pago as PagoModel
from dominio.entidades.pago import Pago


class PagoRepository:
    def obtener_por_id(self, pago_id: int) -> Optional[Pago]:
        try:
            p = PagoModel.objects.get(id=pago_id)
            return self._a_entidad(p)
        except PagoModel.DoesNotExist:
            return None

    def guardar(self, pago: Pago) -> Pago:
        p, _ = PagoModel.objects.update_or_create(
            id=pago.id,
            defaults={
                'comanda_id': pago.comanda_id, 'metodo': pago.metodo,
                'monto': pago.monto, 'vuelto': pago.vuelto,
                'referencia': pago.referencia, 'caja_id': pago.caja_id,
            }
        )
        return self._a_entidad(p)

    def listar_por_comanda(self, comanda_id: int) -> List[Pago]:
        return [self._a_entidad(p) for p in PagoModel.objects.filter(comanda_id=comanda_id)]

    def listar_por_caja(self, caja_id: int) -> List[Pago]:
        return [self._a_entidad(p) for p in PagoModel.objects.filter(caja_id=caja_id)]

    def listar(self) -> List[Pago]:
        return [self._a_entidad(p) for p in PagoModel.objects.all()]

    def total_por_caja(self, caja_id: int) -> float:
        from django.db.models import Sum
        result = PagoModel.objects.filter(caja_id=caja_id).aggregate(total=Sum('monto'))
        return float(result['total'] or 0)

    def listar_por_rango_fecha(self, fecha_inicio, fecha_fin) -> List[Pago]:
        return [
            self._a_entidad(p) for p in PagoModel.objects.filter(
                fecha__date__gte=fecha_inicio,
                fecha__date__lt=fecha_fin
            )
        ]

    def _a_entidad(self, p) -> Pago:
        return Pago(
            id=p.id, comanda_id=p.comanda_id, metodo=p.metodo,
            monto=p.monto, vuelto=p.vuelto, referencia=p.referencia,
            caja_id=p.caja_id,
        )
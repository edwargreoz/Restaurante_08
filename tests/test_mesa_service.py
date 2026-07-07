from django.test import TestCase
from mesas.models import Mesa
from core.excepciones import UnionInvalida


class UnionMesaServiceTest(TestCase):
    def test_crear_union_con_1_mesa_lanza_error(self):
        from mesas.services import UnionMesaService
        mesa = Mesa.objects.create(numero=1, capacidad=4)
        with self.assertRaises(UnionInvalida):
            UnionMesaService.crear([mesa.id])

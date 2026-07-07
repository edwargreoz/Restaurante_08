from django.test import TestCase
from django.contrib.auth.models import User
from core.excepciones import CajaNoAbierta, MesaConComandaActiva


class ComandaServiceTest(TestCase):
    def setUp(self):
        self.usuario = User.objects.create_user(username='test', password='test')

    def test_abrir_sin_caja_lanza_excepcion(self):
        """Verifica que abrir una comanda sin caja activa lance CajaNoAbierta."""
        from pedidos.services import ComandaService
        from mesas.models import Mesa
        mesa = Mesa.objects.create(numero=1, capacidad=4)
        with self.assertRaises(CajaNoAbierta):
            ComandaService.abrir(mesa.id, self.usuario)

    def test_abrir_mesa_ocupada_lanza_excepcion(self):
        """Verifica que abrir comanda en mesa OCUPADA lance error."""
        pass  # Completar

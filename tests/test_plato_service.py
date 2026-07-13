from decimal import Decimal
from django.test import TestCase
from model_bakery import baker
from menu.services import PlatoService
from menu.models import Plato
from inventario.models import Receta
from core.excepciones import RecursoNoEncontrado


class PlatoServiceTests(TestCase):
    def setUp(self):
        self.categoria = baker.make('menu.Categoria', nombre='Pizzas')
        self.receta = baker.make('inventario.Receta', nombre='Receta Pizza')
        self.plato = baker.make(
            'menu.Plato',
            nombre='Margherita',
            precio=Decimal('15.00'),
            categoria=self.categoria,
            disponible=True,
        )

    def test_plato_crear(self):
        plato = PlatoService.crear(
            nombre='Pepperoni',
            precio=Decimal('18.00'),
            categoria_id=self.categoria.id,
            receta_id=self.receta.id,
        )
        self.assertEqual(plato.nombre, 'Pepperoni')
        self.assertTrue(plato.disponible)

    def test_plato_obtener_por_id(self):
        plato = PlatoService.obtener_por_id(self.plato.id)
        self.assertEqual(plato.nombre, 'Margherita')

    def test_plato_obtener_por_id_no_existe(self):
        with self.assertRaises(RecursoNoEncontrado):
            PlatoService.obtener_por_id(9999)

    def test_plato_eliminar_soft_delete(self):
        PlatoService.eliminar(self.plato.id)
        self.plato.refresh_from_db()
        self.assertFalse(self.plato.activo)
        self.assertTrue(Plato.objects.filter(id=self.plato.id).exists())

    def test_plato_toggle_disponible(self):
        self.assertTrue(self.plato.disponible)
        plato = PlatoService.toggle_disponible(self.plato.id)
        self.assertFalse(plato.disponible)
        plato = PlatoService.toggle_disponible(self.plato.id)
        self.assertTrue(plato.disponible)

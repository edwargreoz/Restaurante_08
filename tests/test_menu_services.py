from decimal import Decimal
from django.test import TestCase
from core.excepciones import RecursoNoEncontrado
from menu.models import Categoria, Plato
from menu.services import CategoriaService, PlatoService
from inventario.models import Receta, RecetaInsumo, Insumo


class CategoriaServiceTest(TestCase):
    def setUp(self):
        self.cat = CategoriaService.crear('Entradas', es_bebida=False, orden_display=1)

    def test_crear_categoria(self):
        cat = CategoriaService.crear('Bebidas', es_bebida=True, orden_display=2)
        self.assertTrue(cat.es_bebida)

    def test_listar_categorias(self):
        cats = CategoriaService.listar_categorias()
        self.assertEqual(cats.count(), 1)

    def test_obtener_por_id(self):
        cat = CategoriaService.obtener_por_id(self.cat.id)
        self.assertEqual(cat.nombre, 'Entradas')

    def test_obtener_por_id_no_existe(self):
        with self.assertRaises(RecursoNoEncontrado):
            CategoriaService.obtener_por_id(999)


class PlatoServiceTest(TestCase):
    def setUp(self):
        self.cat = CategoriaService.crear('Platos')
        self.insumo = Insumo.objects.create(
            nombre='Aceite', unidad='ML', stock_actual=Decimal('500'),
        )
        self.receta = Receta.objects.create(nombre='Receta Frita')
        RecetaInsumo.objects.create(
            receta=self.receta, insumo=self.insumo,
            cantidad_por_porcion=Decimal('50'), unidad='ML',
        )
        self.plato = PlatoService.crear(
            'Papa a la Huancaína', Decimal('25.00'),
            self.cat.id, self.receta.id,
        )

    def test_crear_plato(self):
        self.assertEqual(self.plato.nombre, 'Papa a la Huancaína')
        self.assertEqual(self.plato.precio, Decimal('25.00'))

    def test_crear_plato_categoria_no_existe(self):
        with self.assertRaises(RecursoNoEncontrado):
            PlatoService.crear('X', Decimal('10'), 999, self.receta.id)

    def test_crear_plato_receta_no_existe(self):
        with self.assertRaises(RecursoNoEncontrado):
            PlatoService.crear('X', Decimal('10'), self.cat.id, 999)

    def test_obtener_por_id(self):
        p = PlatoService.obtener_por_id(self.plato.id)
        self.assertEqual(p.nombre, 'Papa a la Huancaína')

    def test_obtener_por_id_no_existe(self):
        with self.assertRaises(RecursoNoEncontrado):
            PlatoService.obtener_por_id(999)

    def test_verificar_disponibilidad(self):
        self.assertTrue(PlatoService.verificar_disponibilidad(self.plato.id))

    def test_verificar_no_existe(self):
        with self.assertRaises(RecursoNoEncontrado):
            PlatoService.verificar_disponibilidad(999)

    def test_actualizar(self):
        PlatoService.actualizar(self.plato.id, precio=Decimal('30.00'))
        self.plato.refresh_from_db()
        self.assertEqual(self.plato.precio, Decimal('30.00'))

    def test_eliminar_soft_delete(self):
        pid = self.plato.id
        PlatoService.eliminar(pid)
        self.plato.refresh_from_db()
        self.assertFalse(self.plato.activo)
        self.assertTrue(Plato.objects.filter(id=pid).exists())

    def test_eliminar_no_existe(self):
        with self.assertRaises(RecursoNoEncontrado):
            PlatoService.eliminar(999)

    def test_toggle_disponible(self):
        self.assertTrue(self.plato.disponible)
        PlatoService.toggle_disponible(self.plato.id)
        self.plato.refresh_from_db()
        self.assertFalse(self.plato.disponible)
        PlatoService.toggle_disponible(self.plato.id)
        self.plato.refresh_from_db()
        self.assertTrue(self.plato.disponible)

    def test_toggle_no_existe(self):
        with self.assertRaises(RecursoNoEncontrado):
            PlatoService.toggle_disponible(999)

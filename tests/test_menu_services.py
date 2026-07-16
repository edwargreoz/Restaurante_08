from decimal import Decimal
from django.test import TestCase
from core.excepciones import RecursoNoEncontrado
from menu.models import Categoria, Plato
from menu.services import CategoriaService, PlatoService
from inventario.models import Receta, RecetaInsumo, Insumo
from infraestructura.container import get_container


def _categoria_service():
    return CategoriaService(categoria_repo=get_container().categoria_repo)


def _plato_service():
    container = get_container()
    return PlatoService(
        plato_repo=container.plato_repo,
        categoria_repo=container.categoria_repo,
    )


class CategoriaServiceTest(TestCase):
    def setUp(self):
        self.svc = _categoria_service()
        self.cat = self.svc.crear('Entradas', es_bebida=False, orden_display=1)

    def test_crear_categoria(self):
        cat = self.svc.crear('Bebidas', es_bebida=True, orden_display=2)
        self.assertTrue(cat.es_bebida)

    def test_listar_categorias(self):
        cats = self.svc.listar_categorias()
        self.assertEqual(cats.count(), 1)

    def test_obtener_por_id(self):
        cat = self.svc.obtener_por_id(self.cat.id)
        self.assertEqual(cat.nombre, 'Entradas')

    def test_obtener_por_id_no_existe(self):
        with self.assertRaises(RecursoNoEncontrado):
            self.svc.obtener_por_id(999)


class PlatoServiceTest(TestCase):
    def setUp(self):
        self.cat_svc = _categoria_service()
        self.plato_svc = _plato_service()
        self.cat = self.cat_svc.crear('Platos')
        self.insumo = Insumo.objects.create(
            nombre='Aceite', unidad='ML', stock_actual=Decimal('500'),
        )
        self.receta = Receta.objects.create(nombre='Receta Frita')
        RecetaInsumo.objects.create(
            receta=self.receta, insumo=self.insumo,
            cantidad_por_porcion=Decimal('50'), unidad='ML',
        )
        self.plato = self.plato_svc.crear(
            'Papa a la Huancaína', Decimal('25.00'),
            self.cat.id, self.receta.id,
        )

    def test_crear_plato(self):
        self.assertEqual(self.plato.nombre, 'Papa a la Huancaína')
        self.assertEqual(self.plato.precio, Decimal('25.00'))

    def test_crear_plato_categoria_no_existe(self):
        with self.assertRaises(RecursoNoEncontrado):
            self.plato_svc.crear('X', Decimal('10'), 999, self.receta.id)

    def test_crear_plato_receta_no_existe(self):
        with self.assertRaises(RecursoNoEncontrado):
            self.plato_svc.crear('X', Decimal('10'), self.cat.id, 999)

    def test_obtener_por_id(self):
        p = self.plato_svc.obtener_por_id(self.plato.id)
        self.assertEqual(p.nombre, 'Papa a la Huancaína')

    def test_obtener_por_id_no_existe(self):
        with self.assertRaises(RecursoNoEncontrado):
            self.plato_svc.obtener_por_id(999)

    def test_verificar_disponibilidad(self):
        self.assertTrue(self.plato_svc.verificar_disponibilidad(self.plato.id))

    def test_verificar_no_existe(self):
        with self.assertRaises(RecursoNoEncontrado):
            self.plato_svc.verificar_disponibilidad(999)

    def test_actualizar(self):
        self.plato_svc.actualizar(self.plato.id, precio=Decimal('30.00'))
        plato_db = Plato.objects.get(id=self.plato.id)
        self.assertEqual(plato_db.precio, Decimal('30.00'))

    def test_eliminar_soft_delete(self):
        pid = self.plato.id
        self.plato_svc.eliminar(pid)
        plato_db = Plato.objects.get(id=pid)
        self.assertFalse(plato_db.activo)
        self.assertTrue(Plato.objects.filter(id=pid).exists())

    def test_eliminar_no_existe(self):
        with self.assertRaises(RecursoNoEncontrado):
            self.plato_svc.eliminar(999)

    def test_toggle_disponible(self):
        self.assertTrue(self.plato.disponible)
        self.plato_svc.toggle_disponible(self.plato.id)
        plato_db = Plato.objects.get(id=self.plato.id)
        self.assertFalse(plato_db.disponible)
        self.plato_svc.toggle_disponible(self.plato.id)
        plato_db = Plato.objects.get(id=self.plato.id)
        self.assertTrue(plato_db.disponible)

    def test_toggle_no_existe(self):
        with self.assertRaises(RecursoNoEncontrado):
            self.plato_svc.toggle_disponible(999)

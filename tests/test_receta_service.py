from decimal import Decimal
from django.test import TestCase
from model_bakery import baker
from inventario.services import RecetaService
from inventario.models import Receta, RecetaInsumo
from core.excepciones import RecursoNoEncontrado


class RecetaServiceTests(TestCase):
    def setUp(self):
        self.insumo = baker.make(
            'inventario.Insumo', nombre='Harina',
            unidad='KG', stock_actual=Decimal('50'),
        )

    def test_crear_receta(self):
        insumos_data = [{
            'insumo_id': self.insumo.id,
            'cantidad': Decimal('0.5'),
            'unidad': 'KG',
        }]
        receta = RecetaService.crear(
            nombre='Pizza Margherita',
            insumos_data=insumos_data,
        )
        self.assertEqual(receta.nombre, 'Pizza Margherita')
        self.assertEqual(receta.insumos.count(), 1)

    def test_eliminar_receta_soft_delete(self):
        receta = RecetaService.crear(nombre='Test Receta')
        RecetaService.eliminar(receta.id)
        receta.refresh_from_db()
        self.assertFalse(receta.activo)
        self.assertTrue(Receta.objects.filter(id=receta.id).exists())

    def test_eliminar_insumo_receta_soft_delete(self):
        receta = RecetaService.crear(
            nombre='Receta Test',
            insumos_data=[{
                'insumo_id': self.insumo.id,
                'cantidad': Decimal('1'),
                'unidad': 'KG',
            }],
        )
        ri = RecetaInsumo.objects.filter(receta=receta).first()
        self.assertIsNotNone(ri)
        RecetaService.eliminar_insumo(ri.id)
        ri.refresh_from_db()
        self.assertFalse(ri.activo)

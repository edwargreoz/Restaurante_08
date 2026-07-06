from decimal import Decimal
from django.test import TestCase
from django.contrib.auth.models import User
from core.excepciones import RecursoNoEncontrado, UnidadConversionInvalida
from inventario.models import Insumo, Receta, RecetaInsumo, UnidadConversion
from inventario.services import InsumoService, RecetaService, UnidadConversionService


class UnidadConversionServiceTest(TestCase):
    def setUp(self):
        self.insumo = InsumoService.crear('Harina', 'GR', stock_actual=Decimal('5000'))
        self.unidad_base = UnidadConversion.objects.create(
            nombre='Gramo', es_base=True, insumo=self.insumo,
        )

    def test_crear_cadena_dos_niveles(self):
        cadenas = UnidadConversionService.crear_cadena(self.insumo.id, [
            {'nombre': 'Kg', 'contiene': 1000, 'sub_unidad': 'Gramo'},
        ])
        self.assertEqual(len(cadenas), 1)
        self.assertEqual(cadenas[0].nombre, 'Kg')
        self.assertEqual(cadenas[0].contiene_cantidad, 1000)
        self.assertEqual(cadenas[0].contiene_unidad, self.unidad_base)

    def test_crear_cadena_tres_niveles(self):
        cadenas = UnidadConversionService.crear_cadena(self.insumo.id, [
            {'nombre': 'Saco', 'contiene': 10, 'sub_unidad': 'Kg'},
            {'nombre': 'Kg', 'contiene': 1000, 'sub_unidad': 'Gramo'},
        ])
        self.assertEqual(len(cadenas), 2)
        self.assertEqual(cadenas[0].nombre, 'Saco')
        self.assertEqual(cadenas[1].nombre, 'Kg')

    def test_convertir_un_nivel(self):
        kg = UnidadConversionService.crear_cadena(self.insumo.id, [
            {'nombre': 'Kg', 'contiene': 1000, 'sub_unidad': 'Gramo'},
        ])[0]
        resultado = UnidadConversionService.convertir(kg.id, Decimal('2'))
        self.assertEqual(resultado, Decimal('2000'))

    def test_convertir_dos_niveles(self):
        cadenas = UnidadConversionService.crear_cadena(self.insumo.id, [
            {'nombre': 'Saco', 'contiene': 10, 'sub_unidad': 'Kg'},
            {'nombre': 'Kg', 'contiene': 1000, 'sub_unidad': 'Gramo'},
        ])
        resultado = UnidadConversionService.convertir(cadenas[0].id, Decimal('3'))
        self.assertEqual(resultado, Decimal('30000'))

    def test_convertir_unidad_base_retorna_mismo(self):
        resultado = UnidadConversionService.convertir(self.unidad_base.id, Decimal('500'))
        self.assertEqual(resultado, Decimal('500'))

    def test_convertir_cantidad_cero(self):
        kg = UnidadConversionService.crear_cadena(self.insumo.id, [
            {'nombre': 'Kg', 'contiene': 1000, 'sub_unidad': 'Gramo'},
        ])[0]
        resultado = UnidadConversionService.convertir(kg.id, Decimal('0'))
        self.assertEqual(resultado, Decimal('0'))


class RecetaServiceTest(TestCase):
    def setUp(self):
        self.insumo1 = InsumoService.crear('Tomate', 'UNIDAD', stock_actual=Decimal('50'))
        self.insumo2 = InsumoService.crear('Cebolla', 'UNIDAD', stock_actual=Decimal('30'))

    def test_crear_y_listar_recetas(self):
        receta = RecetaService.crear('Salsa', [
            {'insumo_id': self.insumo1.id, 'cantidad': Decimal('3'), 'unidad': 'UNIDAD'},
            {'insumo_id': self.insumo2.id, 'cantidad': Decimal('2'), 'unidad': 'UNIDAD'},
        ])
        self.assertEqual(receta.nombre, 'Salsa')
        self.assertEqual(receta.insumos.count(), 2)
        self.assertIn(receta, list(RecetaService.listar_recetas()))

    def test_obtener_por_id_prefetch(self):
        receta = RecetaService.crear('Salsa', [
            {'insumo_id': self.insumo1.id, 'cantidad': Decimal('3')},
        ])
        obtenida = RecetaService.obtener_por_id(receta.id)
        self.assertEqual(obtenida.nombre, 'Salsa')
        list(obtenida.insumos.all())

    def test_obtener_por_id_no_existe(self):
        with self.assertRaises(RecursoNoEncontrado):
            RecetaService.obtener_por_id(999)

    def test_actualizar_nombre(self):
        receta = RecetaService.crear('Salsa', [
            {'insumo_id': self.insumo1.id, 'cantidad': Decimal('3')},
        ])
        RecetaService.actualizar(receta.id, nombre='Salsa Actualizada')
        receta.refresh_from_db()
        self.assertEqual(receta.nombre, 'Salsa Actualizada')

    def test_actualizar_insumos(self):
        receta = RecetaService.crear('Salsa', [
            {'insumo_id': self.insumo1.id, 'cantidad': Decimal('3')},
        ])
        self.assertEqual(receta.insumos.count(), 1)
        RecetaService.actualizar(receta.id, insumos_data=[
            {'insumo_id': self.insumo1.id, 'cantidad': Decimal('5')},
            {'insumo_id': self.insumo2.id, 'cantidad': Decimal('2')},
        ])
        self.assertEqual(receta.insumos.count(), 2)

    def test_eliminar_insumo_de_receta(self):
        receta = RecetaService.crear('Salsa', [
            {'insumo_id': self.insumo1.id, 'cantidad': Decimal('3')},
            {'insumo_id': self.insumo2.id, 'cantidad': Decimal('2')},
        ])
        ri = receta.insumos.first()
        RecetaService.eliminar_insumo(ri.id)
        self.assertEqual(receta.insumos.count(), 1)

    def test_eliminar_insumo_no_existe(self):
        with self.assertRaises(RecursoNoEncontrado):
            RecetaService.eliminar_insumo(999)

    def test_calcular_insumos_para_platos(self):
        receta = RecetaService.crear('Salsa', [
            {'insumo_id': self.insumo1.id, 'cantidad': Decimal('3'), 'unidad': 'UNIDAD'},
        ])
        resultado = RecetaService.calcular_insumos_para_platos(receta.id, 2)
        self.assertTrue(resultado['disponible'])
        self.assertEqual(len(resultado['insumos']), 1)
        self.assertEqual(resultado['insumos'][0]['necesario'], Decimal('6'))

    def test_calcular_insumos_stock_insuficiente(self):
        receta = RecetaService.crear('Salsa', [
            {'insumo_id': self.insumo1.id, 'cantidad': Decimal('30'), 'unidad': 'UNIDAD'},
        ])
        resultado = RecetaService.calcular_insumos_para_platos(receta.id, 2)
        self.assertFalse(resultado['disponible'])
        self.assertEqual(len(resultado['faltantes']), 1)

    def test_eliminar_receta(self):
        receta = RecetaService.crear('Salsa', [
            {'insumo_id': self.insumo1.id, 'cantidad': Decimal('3')},
        ])
        rid = receta.id
        RecetaService.eliminar(rid)
        with self.assertRaises(RecursoNoEncontrado):
            RecetaService.obtener_por_id(rid)


class InsumoServiceTest(TestCase):
    def setUp(self):
        self.insumo = InsumoService.crear('Arroz', 'KG', stock_actual=Decimal('10'))

    def test_crear_insumo(self):
        insumo = InsumoService.crear('Azúcar', 'KG')
        self.assertEqual(insumo.nombre, 'Azúcar')
        self.assertEqual(insumo.stock_actual, Decimal('0'))

    def test_obtener_por_id(self):
        obtenido = InsumoService.obtener_por_id(self.insumo.id)
        self.assertEqual(obtenido.nombre, 'Arroz')

    def test_obtener_por_id_no_existe(self):
        with self.assertRaises(RecursoNoEncontrado):
            InsumoService.obtener_por_id(999)

    def test_actualizar(self):
        InsumoService.actualizar(self.insumo.id, nombre='Arroz Integral', stock_minimo=Decimal('5'))
        self.insumo.refresh_from_db()
        self.assertEqual(self.insumo.nombre, 'Arroz Integral')
        self.assertEqual(self.insumo.stock_minimo, Decimal('5'))

    def test_ajustar_stock(self):
        mov = InsumoService.ajustar_stock(
            self.insumo.id, Decimal('20'), motivo='Ajuste manual'
        )
        self.insumo.refresh_from_db()
        self.assertEqual(self.insumo.stock_actual, Decimal('20'))
        self.assertEqual(mov.tipo, 'AJUSTE')
        self.assertEqual(mov.observacion, 'Ajuste manual')

    def test_ajustar_stock_negativo(self):
        with self.assertRaises(Exception):
            InsumoService.ajustar_stock(self.insumo.id, Decimal('-5'), motivo='Invalido')

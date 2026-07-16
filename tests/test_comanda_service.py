from django.test import TestCase
from django.contrib.auth.models import User
from decimal import Decimal
from core.excepciones import (
    CajaNoAbierta, MesaConComandaActiva, ComandaNoDisponible,
    StockInsuficiente, AppError,
)
from pedidos.services import ComandaService, LineaComandaService
from pedidos.models import Comanda, LineaComanda
from mesas.models import Mesa
from menu.models import Categoria, Plato
from inventario.models import Insumo, Receta, RecetaInsumo
from caja.models import Caja
from caja.services import CajaService
from infraestructura.container import get_container


class ComandaServiceTest(TestCase):
    def setUp(self):
        self.usuario = User.objects.create_user(username='mozo', password='test')
        self.mesa = Mesa.objects.create(numero=1, capacidad=4)
        container = get_container()
        self.comanda_service = ComandaService(
            comanda_repo=container.comanda_repo,
            mesa_repo=container.mesa_repo,
        )

    def _abrir_caja(self):
        container = get_container()
        caja_svc = CajaService(caja_repo=container.caja_repo)
        return caja_svc.abrir_turno(
            turno_nombre='TEST', usuario=self.usuario, saldo_inicial=Decimal('100.00')
        )

    def _crear_plato_con_receta(self, nombre='Lomo Saltado', precio=Decimal('25.00'), stock=Decimal('10')):
        cat = Categoria.objects.create(nombre='Platos Fuertes')
        receta = Receta.objects.create(nombre=f'Receta {nombre}')
        insumo = Insumo.objects.create(
            nombre=f'Insumo {nombre}', unidad='KG',
            stock_actual=stock, stock_minimo=Decimal('1'), costo_unitario=Decimal('5')
        )
        RecetaInsumo.objects.create(
            receta=receta, insumo=insumo,
            cantidad_por_porcion=Decimal('0.5'), unidad='KG',
        )
        plato = Plato.objects.create(
            nombre=nombre, precio=precio,
            categoria=cat, receta=receta,
        )
        return plato, insumo

    # ── Test: abrir sin caja ──
    def test_abrir_sin_caja_lanza_excepcion(self):
        """Verifica que abrir una comanda sin caja activa lance CajaNoAbierta."""
        with self.assertRaises(CajaNoAbierta):
            self.comanda_service.abrir(self.mesa.id, self.usuario)

    # ── Test: abrir mesa ya ocupada ──
    def test_abrir_mesa_ocupada_lanza_excepcion(self):
        """Verifica que abrir comanda en mesa OCUPADA lance MesaConComandaActiva."""
        self._abrir_caja()
        self.mesa.estado = 'OCUPADA'
        self.mesa.save()
        with self.assertRaises(MesaConComandaActiva):
            self.comanda_service.abrir(self.mesa.id, self.usuario)

    # ── Test: abrir comanda correctamente ──
    def test_abrir_comanda_ok(self):
        self._abrir_caja()
        comanda = self.comanda_service.abrir(self.mesa.id, self.usuario)
        self.assertEqual(comanda.estado, 'ABIERTA')
        self.assertEqual(comanda.mozo, self.usuario)
        self.mesa.refresh_from_db()
        self.assertEqual(self.mesa.estado, 'OCUPADA')

    # ── Test: agregar platos con stock ──
    def test_agregar_platos_descuenta_stock(self):
        self._abrir_caja()
        comanda = self.comanda_service.abrir(self.mesa.id, self.usuario)
        plato, insumo = self._crear_plato_con_receta(stock=Decimal('10'))
        self.comanda_service.agregar_platos(
            comanda.id,
            [{'plato_id': plato.id, 'cantidad': 2, 'observacion': ''}],
            usuario=self.usuario,
        )
        insumo.refresh_from_db()
        # 10 - (0.5 * 2) = 9.0
        self.assertEqual(insumo.stock_actual, Decimal('9.00'))
        self.assertEqual(comanda.lineas.count(), 1)

    # ── Test: agregar platos sin stock lanza excepción ──
    def test_agregar_platos_sin_stock_lanza_excepcion(self):
        self._abrir_caja()
        comanda = self.comanda_service.abrir(self.mesa.id, self.usuario)
        plato, insumo = self._crear_plato_con_receta(
            nombre='Ceviche', stock=Decimal('0.1')
        )
        with self.assertRaises(StockInsuficiente):
            self.comanda_service.agregar_platos(
                comanda.id,
                [{'plato_id': plato.id, 'cantidad': 5, 'observacion': ''}],
                usuario=self.usuario,
            )

    # ── Test: insumo agotado marca plato como no disponible ──
    def test_insumo_agotado_marca_plato_no_disponible(self):
        self._abrir_caja()
        comanda = self.comanda_service.abrir(self.mesa.id, self.usuario)
        plato, insumo = self._crear_plato_con_receta(
            nombre='Aji de Gallina', stock=Decimal('0.5')
        )
        self.assertTrue(plato.disponible)
        self.comanda_service.agregar_platos(
            comanda.id,
            [{'plato_id': plato.id, 'cantidad': 1, 'observacion': ''}],
            usuario=self.usuario,
        )
        insumo.refresh_from_db()
        plato.refresh_from_db()
        self.assertEqual(insumo.stock_actual, Decimal('0.00'))
        self.assertFalse(plato.disponible)

    # ── Test: anular comanda restaura stock ──
    def test_anular_comanda_restaura_stock(self):
        self._abrir_caja()
        comanda = self.comanda_service.abrir(self.mesa.id, self.usuario)
        plato, insumo = self._crear_plato_con_receta(
            nombre='Arroz con Pollo', stock=Decimal('5')
        )
        self.comanda_service.agregar_platos(
            comanda.id,
            [{'plato_id': plato.id, 'cantidad': 2, 'observacion': ''}],
            usuario=self.usuario,
        )
        insumo.refresh_from_db()
        self.assertEqual(insumo.stock_actual, Decimal('4.00'))

        self.comanda_service.anular(comanda.id, usuario=self.usuario)
        comanda.refresh_from_db()
        insumo.refresh_from_db()
        self.assertEqual(comanda.estado, 'ANULADA')
        self.assertEqual(insumo.stock_actual, Decimal('5.00'))

    # ── Test: anular comanda ya cobrada falla ──
    def test_anular_comanda_cobrada_falla(self):
        self._abrir_caja()
        comanda = self.comanda_service.abrir(self.mesa.id, self.usuario)
        comanda.estado = 'COBRADA'
        comanda.save(update_fields=['estado'])
        with self.assertRaises(ComandaNoDisponible):
            self.comanda_service.anular(comanda.id, usuario=self.usuario)

    # ── Test: pagar comanda ──
    def test_pagar_comanda_ok(self):
        self._abrir_caja()
        comanda = self.comanda_service.abrir(self.mesa.id, self.usuario)
        plato, _ = self._crear_plato_con_receta(
            nombre='Causa', stock=Decimal('10')
        )
        self.comanda_service.agregar_platos(
            comanda.id,
            [{'plato_id': plato.id, 'cantidad': 1, 'observacion': ''}],
            usuario=self.usuario,
        )
        comanda.estado = 'LISTA'
        comanda.save(update_fields=['estado'])
        self.comanda_service.pagar(
            comanda.id, metodo='EFECTIVO',
            monto=Decimal('50.00'), vuelto=Decimal('25.00'),
        )
        comanda.refresh_from_db()
        self.assertEqual(comanda.estado, 'COBRADA')
        self.mesa.refresh_from_db()
        self.assertEqual(self.mesa.estado, 'LIMPIEZA')

    # ── Test: fusionar comandas ──
    def test_fusionar_comandas(self):
        self._abrir_caja()
        mesa2 = Mesa.objects.create(numero=2, capacidad=4)
        c1 = self.comanda_service.abrir(self.mesa.id, self.usuario)
        c2 = self.comanda_service.abrir(mesa2.id, self.usuario)
        plato, _ = self._crear_plato_con_receta(
            nombre='Tacu Tacu', stock=Decimal('20')
        )
        self.comanda_service.agregar_platos(
            c2.id,
            [{'plato_id': plato.id, 'cantidad': 1, 'observacion': ''}],
            usuario=self.usuario,
        )
        resultado = self.comanda_service.fusionar(c1.id, c2.id)
        c2.refresh_from_db()
        self.assertEqual(c2.estado, 'ANULADA')
        self.assertEqual(resultado.lineas.count(), 1)


class LineaComandaServiceTest(TestCase):
    def setUp(self):
        self.usuario = User.objects.create_user(username='cocinero', password='test')
        self.mesa = Mesa.objects.create(numero=10, capacidad=4)
        container = get_container()
        CajaService(caja_repo=container.caja_repo).abrir_turno(
            turno_nombre='TEST', usuario=self.usuario, saldo_inicial=Decimal('100.00')
        )
        self.comanda_service = ComandaService(
            comanda_repo=container.comanda_repo,
            mesa_repo=container.mesa_repo,
        )
        self.linea_service = LineaComandaService(
            linea_comanda_repo=container.linea_comanda_repo,
        )
        self.comanda = self.comanda_service.abrir(self.mesa.id, self.usuario)
        cat = Categoria.objects.create(nombre='Entradas')
        self.plato = Plato.objects.create(
            nombre='Papa a la Huancaina', precio=Decimal('12'),
            categoria=cat,
        )
        self.linea = LineaComanda.objects.create(
            comanda=self.comanda, plato=self.plato, cantidad=1,
        )

    def test_enviar_cocina(self):
        self.linea_service.enviar_cocina(self.linea.id)
        self.linea.refresh_from_db()
        self.assertEqual(self.linea.estado, 'EN_PREP')

    def test_marcar_listo(self):
        self.linea_service.enviar_cocina(self.linea.id)
        self.linea_service.marcar_listo(self.linea.id)
        self.linea.refresh_from_db()
        self.assertEqual(self.linea.estado, 'LISTO')

    def test_marcar_listo_sin_enviar_falla(self):
        with self.assertRaises(AppError):
            self.linea_service.marcar_listo(self.linea.id)

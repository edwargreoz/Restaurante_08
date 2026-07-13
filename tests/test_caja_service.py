from decimal import Decimal
from django.test import TestCase
from django.contrib.auth.models import User
from core.excepciones import CajaNoAbierta, RecursoNoEncontrado, ReglaNegocioViolada
from caja.models import Caja, Pago
from caja.services import CajaService, PagoService, ReporteService
from mesas.models import Mesa
from pedidos.models import Comanda


class CajaServiceTest(TestCase):
    def setUp(self):
        self.usuario = User.objects.create_user(username='cajero', password='pass123')

    def test_abrir_turno_ok(self):
        caja = CajaService.abrir_turno('TARDE', self.usuario, saldo_inicial=Decimal('100'))
        self.assertEqual(caja.turno, 'TARDE')
        self.assertEqual(caja.cajero, self.usuario)
        self.assertEqual(caja.estado, 'ABIERTA')
        self.assertEqual(caja.saldo_inicial, Decimal('100'))

    def test_abrir_turno_duplicado(self):
        CajaService.abrir_turno('MAÑANA', self.usuario)
        with self.assertRaises(ReglaNegocioViolada):
            CajaService.abrir_turno('TARDE', self.usuario)

    def test_obtener_activa_existe(self):
        CajaService.abrir_turno('MAÑANA', self.usuario)
        caja = CajaService.obtener_activa()
        self.assertIsNotNone(caja)
        self.assertEqual(caja.estado, 'ABIERTA')

    def test_obtener_activa_no_existe(self):
        with self.assertRaises(CajaNoAbierta):
            CajaService.obtener_activa()

    def test_cerrar_turno_ok(self):
        caja = CajaService.abrir_turno('MAÑANA', self.usuario)
        resultado = CajaService.cerrar_turno(caja.id)
        self.assertEqual(resultado['total_ventas'], Decimal('0'))
        caja.refresh_from_db()
        self.assertEqual(caja.estado, 'CERRADA')

    def test_cerrar_turno_no_existe(self):
        with self.assertRaises(RecursoNoEncontrado):
            CajaService.cerrar_turno(999)

    def test_listar_todas(self):
        CajaService.abrir_turno('MAÑANA', self.usuario)
        CajaService.obtener_activa()
        Caja.objects.create(
            turno='CERRADA', cajero=self.usuario,
            saldo_inicial=Decimal('0'), estado='CERRADA',
        )
        todas = CajaService.listar_todas()
        self.assertEqual(todas.count(), 2)


class PagoServiceTest(TestCase):
    def setUp(self):
        self.usuario = User.objects.create_user(username='cajero', password='pass123')
        self.caja = CajaService.abrir_turno('TARDE', self.usuario)
        self.mesa = Mesa.objects.create(numero=1, capacidad=4)
        self.comanda = Comanda.objects.create(
            mesa=self.mesa, mozo=self.usuario, estado='COBRADA',
        )

    def test_reporte_sin_pagos(self):
        reporte = PagoService.reporte_ventas()
        self.assertEqual(reporte['total_general'], Decimal('0'))
        self.assertEqual(reporte['total_pagos'], 0)

    def test_reporte_con_pagos(self):
        for _ in range(3):
            Pago.objects.create(
                comanda=self.comanda, caja=self.caja, metodo='EFECTIVO',
                monto=Decimal('100'), vuelto=Decimal('0'),
            )
        reporte = PagoService.reporte_ventas()
        self.assertEqual(reporte['total_general'], Decimal('300'))
        self.assertEqual(reporte['total_pagos'], 3)

    def test_reporte_filtro_caja(self):
        for _ in range(2):
            Pago.objects.create(
                comanda=self.comanda, caja=self.caja, metodo='EFECTIVO',
                monto=Decimal('50'), vuelto=Decimal('0'),
            )
        otra_caja = Caja.objects.create(
            turno='OTRO', cajero=self.usuario, saldo_inicial=Decimal('0'),
            estado='CERRADA',
        )
        otra_comanda = Comanda.objects.create(
            mesa=self.mesa, mozo=self.usuario, estado='COBRADA',
        )
        Pago.objects.create(
            comanda=otra_comanda, caja=otra_caja, metodo='YAPE',
            monto=Decimal('200'), vuelto=Decimal('0'),
        )
        reporte = PagoService.reporte_ventas(caja_id=self.caja.id)
        self.assertEqual(reporte['total_general'], Decimal('100'))
        self.assertEqual(reporte['total_pagos'], 2)

    def test_reporte_ticket_promedio(self):
        Pago.objects.create(
            comanda=self.comanda, caja=self.caja, metodo='EFECTIVO',
            monto=Decimal('200'), vuelto=Decimal('0'),
        )
        Pago.objects.create(
            comanda=self.comanda, caja=self.caja, metodo='EFECTIVO',
            monto=Decimal('100'), vuelto=Decimal('0'),
        )
        reporte = PagoService.reporte_ventas()
        self.assertEqual(reporte['ticket_promedio'], Decimal('150'))

    def test_reporte_por_metodo(self):
        Pago.objects.create(
            comanda=self.comanda, caja=self.caja, metodo='EFECTIVO',
            monto=Decimal('100'), vuelto=Decimal('0'),
        )
        Pago.objects.create(
            comanda=self.comanda, caja=self.caja, metodo='YAPE',
            monto=Decimal('50'), vuelto=Decimal('0'),
        )
        reporte = PagoService.reporte_ventas()
        self.assertEqual(len(reporte['por_metodo']), 2)

    def test_obtener_comanda_para_cobro_no_existe(self):
        with self.assertRaises(RecursoNoEncontrado):
            PagoService.obtener_comanda_para_cobro(999)

    def test_obtener_comanda_para_cobro_no_lista(self):
        with self.assertRaises(RecursoNoEncontrado):
            PagoService.obtener_comanda_para_cobro(self.comanda.id)

    def test_listar_comandas_para_cobro(self):
        self.comanda.estado = 'ABIERTA'
        self.comanda.save()
        resultado = PagoService.listar_comandas_para_cobro()
        self.assertEqual(resultado.count(), 1)


class ReporteServiceTest(TestCase):
    def setUp(self):
        self.usuario = User.objects.create_user(username='admin', password='test')

    def test_stock_critico_vacio(self):
        resultado = ReporteService.stock_critico()
        self.assertEqual(resultado.count(), 0)

    def test_top_platos_vacio(self):
        resultado = ReporteService.top_platos()
        self.assertEqual(len(list(resultado)), 0)

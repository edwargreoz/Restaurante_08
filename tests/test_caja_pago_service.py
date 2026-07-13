from decimal import Decimal
from django.test import TestCase
from model_bakery import baker
from caja.services import CajaService, PagoService
from caja.models import Caja


class PagoServiceTests(TestCase):
    def setUp(self):
        self.usuario = baker.make('auth.User', username='cajero1')
        self.caja = baker.make(
            'caja.Caja', cajero=self.usuario,
            saldo_inicial=Decimal('100.00'), estado='ABIERTA',
        )
        self.mesa = baker.make('mesas.Mesa', numero=1, estado='OCUPADA')
        self.comanda = baker.make(
            'pedidos.Comanda', mesa=self.mesa, mozo=self.usuario,
            estado='LISTA',
        )

    def test_reporte_ventas_sin_pagos(self):
        data = PagoService.reporte_ventas(caja_id=self.caja.id)
        self.assertEqual(data['total_general'], Decimal('0'))
        self.assertEqual(data['total_pagos'], 0)

    def test_listar_comandas_para_cobro(self):
        comandas = PagoService.listar_comandas_para_cobro()
        self.assertIn(self.comanda, comandas)

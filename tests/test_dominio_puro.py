"""
Tests de dominio puro — SIN base de datos.
Validan la lógica de negocio de las entidades dataclass
usando unittest.TestCase (no Django TestCase).
"""
import unittest
from decimal import Decimal
from datetime import date, time

from core.excepciones import TransicionEstadoInvalida, ReglaNegocioViolada


class ComandaDominioTest(unittest.TestCase):
    def test_crear_comanda_defaultstate_abierta(self):
        from dominio.entidades.comanda import Comanda
        c = Comanda(id=None, mesa_id=1, mozo_id=1)
        self.assertEqual(c.estado, 'ABIERTA')
        self.assertEqual(c.total, Decimal('0'))

    def test_transicion_abierta_a_en_preparacion(self):
        from dominio.entidades.comanda import Comanda
        c = Comanda(id=1, mesa_id=1, mozo_id=1, estado='ABIERTA')
        c.cambiar_estado('EN_PREPARACION')
        self.assertEqual(c.estado, 'EN_PREPARACION')

    def test_transicion_en_preparacion_a_lista(self):
        from dominio.entidades.comanda import Comanda
        c = Comanda(id=1, mesa_id=1, mozo_id=1, estado='EN_PREPARACION')
        c.cambiar_estado('LISTA')
        self.assertEqual(c.estado, 'LISTA')

    def test_transicion_lista_a_cobrada(self):
        from dominio.entidades.comanda import Comanda
        c = Comanda(id=1, mesa_id=1, mozo_id=1, estado='LISTA')
        c.cambiar_estado('COBRADA')
        self.assertEqual(c.estado, 'COBRADA')

    def test_transicion_abierta_a_anulada(self):
        from dominio.entidades.comanda import Comanda
        c = Comanda(id=1, mesa_id=1, mozo_id=1, estado='ABIERTA')
        c.cambiar_estado('ANULADA')
        self.assertEqual(c.estado, 'ANULADA')

    def test_transicion_invalida_abierta_a_cobrada(self):
        from dominio.entidades.comanda import Comanda
        c = Comanda(id=1, mesa_id=1, mozo_id=1, estado='ABIERTA')
        with self.assertRaises(TransicionEstadoInvalida):
            c.cambiar_estado('COBRADA')

    def test_transicion_invalida_cobrada_a_lista(self):
        from dominio.entidades.comanda import Comanda
        c = Comanda(id=1, mesa_id=1, mozo_id=1, estado='COBRADA')
        with self.assertRaises(TransicionEstadoInvalida):
            c.cambiar_estado('LISTA')

    def test_transicion_invalida_anulada_a_cualquier(self):
        from dominio.entidades.comanda import Comanda
        c = Comanda(id=1, mesa_id=1, mozo_id=1, estado='ANULADA')
        with self.assertRaises(TransicionEstadoInvalida):
            c.cambiar_estado('ABIERTA')


class LineaComandaDominioTest(unittest.TestCase):
    def test_crear_linea_estado_pendiente(self):
        from dominio.entidades.linea_comanda import LineaComanda
        lc = LineaComanda(id=None, comanda_id=1, plato_id=1)
        self.assertEqual(lc.estado, 'PENDIENTE')
        self.assertEqual(lc.cantidad, 1)

    def test_transicion_pendiente_a_en_prep(self):
        from dominio.entidades.linea_comanda import LineaComanda
        lc = LineaComanda(id=1, comanda_id=1, plato_id=1, estado='PENDIENTE')
        lc.cambiar_estado('EN_PREP')
        self.assertEqual(lc.estado, 'EN_PREP')

    def test_transicion_en_prep_a_listo(self):
        from dominio.entidades.linea_comanda import LineaComanda
        lc = LineaComanda(id=1, comanda_id=1, plato_id=1, estado='EN_PREP')
        lc.cambiar_estado('LISTO')
        self.assertEqual(lc.estado, 'LISTO')

    def test_transicion_listo_a_entregado(self):
        from dominio.entidades.linea_comanda import LineaComanda
        lc = LineaComanda(id=1, comanda_id=1, plato_id=1, estado='LISTO')
        lc.cambiar_estado('ENTREGADO')
        self.assertEqual(lc.estado, 'ENTREGADO')

    def test_transicion_invalida_pendiente_a_listo(self):
        from dominio.entidades.linea_comanda import LineaComanda
        lc = LineaComanda(id=1, comanda_id=1, plato_id=1, estado='PENDIENTE')
        with self.assertRaises(TransicionEstadoInvalida):
            lc.cambiar_estado('LISTO')

    def test_transicion_invalida_entregado_a_cualquier(self):
        from dominio.entidades.linea_comanda import LineaComanda
        lc = LineaComanda(id=1, comanda_id=1, plato_id=1, estado='ENTREGADO')
        with self.assertRaises(TransicionEstadoInvalida):
            lc.cambiar_estado('PENDIENTE')

    def test_transicion_invalida_listo_a_en_prep(self):
        from dominio.entidades.linea_comanda import LineaComanda
        lc = LineaComanda(id=1, comanda_id=1, plato_id=1, estado='LISTO')
        with self.assertRaises(TransicionEstadoInvalida):
            lc.cambiar_estado('EN_PREP')


class MesaDominioTest(unittest.TestCase):
    def test_crear_mesa_estado_libre(self):
        from dominio.entidades.mesa import Mesa
        m = Mesa(id=None, numero=1, capacidad=4)
        self.assertEqual(m.estado, 'LIBRE')
        self.assertEqual(m.zona, 'SALON')

    def test_ocupar_desde_libre(self):
        from dominio.entidades.mesa import Mesa
        m = Mesa(id=1, numero=1, capacidad=4, estado='LIBRE')
        m.ocupar()
        self.assertEqual(m.estado, 'OCUPADA')

    def test_ocupar_desde_reservada(self):
        from dominio.entidades.mesa import Mesa
        m = Mesa(id=1, numero=1, capacidad=4, estado='RESERVADA')
        m.ocupar()
        self.assertEqual(m.estado, 'OCUPADA')

    def test_ocupar_desde_ocupada_falla(self):
        from dominio.entidades.mesa import Mesa
        m = Mesa(id=1, numero=1, capacidad=4, estado='OCUPADA')
        with self.assertRaises(ReglaNegocioViolada):
            m.ocupar()

    def test_ocupar_desde_limpieza_falla(self):
        from dominio.entidades.mesa import Mesa
        m = Mesa(id=1, numero=1, capacidad=4, estado='LIMPIEZA')
        with self.assertRaises(ReglaNegocioViolada):
            m.ocupar()

    def test_liberar_mesa(self):
        from dominio.entidades.mesa import Mesa
        m = Mesa(id=1, numero=1, capacidad=4, estado='OCUPADA')
        m.liberar()
        self.assertEqual(m.estado, 'LIBRE')

    def test_limpiar_mesa(self):
        from dominio.entidades.mesa import Mesa
        m = Mesa(id=1, numero=1, capacidad=4, estado='OCUPADA')
        m.limpiar()
        self.assertEqual(m.estado, 'LIMPIEZA')

    def test_reservar_mesa(self):
        from dominio.entidades.mesa import Mesa
        m = Mesa(id=1, numero=1, capacidad=4, estado='LIBRE')
        m.reservar()
        self.assertEqual(m.estado, 'RESERVADA')


class InsumoDominioTest(unittest.TestCase):
    def test_stock_critico_true(self):
        from dominio.entidades.insumo import Insumo
        i = Insumo(id=1, nombre='Arroz', unidad='KG',
                    stock_actual=Decimal('2'), stock_minimo=Decimal('5'))
        self.assertTrue(i.stock_critico)

    def test_stock_critico_false(self):
        from dominio.entidades.insumo import Insumo
        i = Insumo(id=1, nombre='Arroz', unidad='KG',
                    stock_actual=Decimal('10'), stock_minimo=Decimal('5'))
        self.assertFalse(i.stock_critico)

    def test_deducir_stock_ok(self):
        from dominio.entidades.insumo import Insumo
        i = Insumo(id=1, nombre='Arroz', unidad='KG',
                    stock_actual=Decimal('10'))
        i.deducir_stock(Decimal('3'))
        self.assertEqual(i.stock_actual, Decimal('7'))

    def test_deducir_stock_insuficiente(self):
        from dominio.entidades.insumo import Insumo
        from core.excepciones import StockInsuficiente
        i = Insumo(id=1, nombre='Arroz', unidad='KG',
                    stock_actual=Decimal('2'))
        with self.assertRaises(StockInsuficiente):
            i.deducir_stock(Decimal('5'))

    def test_reponer_stock(self):
        from dominio.entidades.insumo import Insumo
        i = Insumo(id=1, nombre='Arroz', unidad='KG',
                    stock_actual=Decimal('5'))
        i.reponer_stock(Decimal('3'))
        self.assertEqual(i.stock_actual, Decimal('8'))


class ReservaDominioTest(unittest.TestCase):
    def test_crear_reserva(self):
        from dominio.entidades.reserva import Reserva
        r = Reserva(
            id=None, mesa_id=1, union_mesa_id=None,
            cliente_nombre='Juan', fecha=date(2026, 7, 15),
            hora_inicio=time(12, 0), hora_fin=time(14, 0),
            num_personas=4,
        )
        self.assertTrue(r.activo)
        self.assertFalse(r.finalizada)


class UnionMesaDominioTest(unittest.TestCase):
    def test_crear_union(self):
        from dominio.entidades.union_mesa import UnionMesa
        u = UnionMesa(id=None, mesa_ids=[1, 2])
        self.assertTrue(u.activo)
        self.assertEqual(len(u.mesa_ids), 2)


class PagoDominioTest(unittest.TestCase):
    def test_crear_pago(self):
        from dominio.entidades.pago import Pago
        p = Pago(id=None, comanda_id=1, metodo='EFECTIVO',
                 monto=Decimal('50.00'), vuelto=Decimal('5.00'))
        self.assertEqual(p.monto, Decimal('50.00'))
        self.assertEqual(p.vuelto, Decimal('5.00'))


class CajaDominioTest(unittest.TestCase):
    def test_crear_caja(self):
        from dominio.entidades.caja import Caja
        c = Caja(id=None, turno='MAÑANA', cajero_id=1,
                 saldo_inicial=Decimal('200'))
        self.assertEqual(c.estado, 'ABIERTA')
        self.assertEqual(c.saldo_inicial, Decimal('200'))


class PlatoDominioTest(unittest.TestCase):
    def test_crear_plato(self):
        from dominio.entidades.plato import Plato
        p = Plato(id=None, nombre='Lomo Saltado',
                  precio=Decimal('25.00'), categoria_id=1,
                  receta_id=1)
        self.assertTrue(p.disponible)
        self.assertEqual(p.tiempo_preparacion_min, 15)


class CategoriaDominioTest(unittest.TestCase):
    def test_crear_categoria(self):
        from dominio.entidades.categoria import Categoria
        c = Categoria(id=None, nombre='Bebidas', es_bebida=True)
        self.assertTrue(c.es_bebida)
        self.assertEqual(c.orden_display, 0)


class PuertosProtocolTest(unittest.TestCase):
    def test_icomanda_repository_methods(self):
        from dominio.puertos.repositorios import IComandaRepository
        self.assertTrue(hasattr(IComandaRepository, 'obtener_por_id'))
        self.assertTrue(hasattr(IComandaRepository, 'guardar'))

    def test_imesa_repository_methods(self):
        from dominio.puertos.repositorios import IMesaRepository
        self.assertTrue(hasattr(IMesaRepository, 'obtener_por_id'))
        self.assertTrue(hasattr(IMesaRepository, 'guardar'))
        self.assertTrue(hasattr(IMesaRepository, 'listar_activas'))

    def test_iinsumo_repository_methods(self):
        from dominio.puertos.repositorios import IInsumoRepository
        self.assertTrue(hasattr(IInsumoRepository, 'obtener_por_id'))
        self.assertTrue(hasattr(IInsumoRepository, 'guardar'))

    def test_icaja_repository_methods(self):
        from dominio.puertos.repositorios import ICajaRepository
        self.assertTrue(hasattr(ICajaRepository, 'obtener_abierta'))
        self.assertTrue(hasattr(ICajaRepository, 'guardar'))


if __name__ == '__main__':
    unittest.main()

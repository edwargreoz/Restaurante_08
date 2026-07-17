from datetime import date, time
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth.models import User
from core.excepciones import (
    RecursoNoEncontrado, CapacidadExcedida, ReglaNegocioViolada,
)
from reservas.services import ReservaService
from reservas.models import Reserva
from mesas.models import Mesa
from infraestructura.container import get_container


class ReservaServiceTest(TestCase):
    def setUp(self):
        self.usuario = User.objects.create_user(username='mozo', password='test')
        self.mesa = Mesa.objects.create(numero=1, capacidad=4, estado='LIBRE')
        container = get_container()
        self.svc = container.reserva_service

    def test_crear_reserva_ok(self):
        reserva = self.svc.crear(
            mesas_ids=[self.mesa.id],
            fecha=date(2026, 8, 1),
            hora_inicio='12:00', hora_fin='14:00',
            num_personas=2, cliente_nombre='Juan Perez',
        )
        self.assertEqual(reserva.cliente_nombre, 'Juan Perez')
        self.assertEqual(reserva.num_personas, 2)
        self.assertTrue(reserva.activo)

    def test_crear_reserva_sin_mesas_lanza_error(self):
        with self.assertRaises(ReglaNegocioViolada):
            self.svc.crear(
                mesas_ids=[],
                fecha=date(2026, 8, 1),
                hora_inicio='12:00', hora_fin='14:00',
                num_personas=2, cliente_nombre='Juan',
            )

    def test_crear_reserva_mesa_no_existe(self):
        with self.assertRaises(ReglaNegocioViolada):
            self.svc.crear(
                mesas_ids=[999],
                fecha=date(2026, 8, 1),
                hora_inicio='12:00', hora_fin='14:00',
                num_personas=2, cliente_nombre='Juan',
            )

    def test_crear_reserva_mesa_no_libre(self):
        self.mesa.estado = 'OCUPADA'
        self.mesa.save()
        with self.assertRaises(ReglaNegocioViolada):
            self.svc.crear(
                mesas_ids=[self.mesa.id],
                fecha=date(2026, 8, 1),
                hora_inicio='12:00', hora_fin='14:00',
                num_personas=2, cliente_nombre='Juan',
            )

    def test_crear_reserva_capacidad_excedida(self):
        with self.assertRaises(CapacidadExcedida):
            self.svc.crear(
                mesas_ids=[self.mesa.id],
                fecha=date(2026, 8, 1),
                hora_inicio='12:00', hora_fin='14:00',
                num_personas=10, cliente_nombre='Juan',
            )

    def test_crear_reserva_hora_fuera_rango(self):
        with self.assertRaises(ReglaNegocioViolada):
            self.svc.crear(
                mesas_ids=[self.mesa.id],
                fecha=date(2026, 8, 1),
                hora_inicio='05:00', hora_fin='07:00',
                num_personas=2, cliente_nombre='Juan',
            )

    def test_crear_reserva_hora_inicio_mayor_que_fin(self):
        with self.assertRaises(ReglaNegocioViolada):
            self.svc.crear(
                mesas_ids=[self.mesa.id],
                fecha=date(2026, 8, 1),
                hora_inicio='14:00', hora_fin='12:00',
                num_personas=2, cliente_nombre='Juan',
            )

    def test_crear_reserva_celular_invalido(self):
        with self.assertRaises(ReglaNegocioViolada):
            self.svc.crear(
                mesas_ids=[self.mesa.id],
                fecha=date(2026, 8, 1),
                hora_inicio='12:00', hora_fin='14:00',
                num_personas=2, cliente_nombre='Juan',
                cliente_contacto='123',
            )

    def test_crear_reserva_email_invalido(self):
        with self.assertRaises(ReglaNegocioViolada):
            self.svc.crear(
                mesas_ids=[self.mesa.id],
                fecha=date(2026, 8, 1),
                hora_inicio='12:00', hora_fin='14:00',
                num_personas=2, cliente_nombre='Juan',
                cliente_contacto='email_invalido',
            )

    def test_crear_reserva_celular_valido(self):
        reserva = self.svc.crear(
            mesas_ids=[self.mesa.id],
            fecha=date(2026, 8, 1),
            hora_inicio='12:00', hora_fin='14:00',
            num_personas=2, cliente_nombre='Juan',
            cliente_contacto='987654321',
        )
        self.assertEqual(reserva.cliente_contacto, '987654321')

    def test_crear_reserva_email_valido(self):
        reserva = self.svc.crear(
            mesas_ids=[self.mesa.id],
            fecha=date(2026, 8, 1),
            hora_inicio='12:00', hora_fin='14:00',
            num_personas=2, cliente_nombre='Juan',
            cliente_contacto='juan@test.com',
        )
        self.assertEqual(reserva.cliente_contacto, 'juan@test.com')

    def test_cancelar_reserva_ok(self):
        reserva = self.svc.crear(
            mesas_ids=[self.mesa.id],
            fecha=date(2026, 8, 1),
            hora_inicio='12:00', hora_fin='14:00',
            num_personas=2, cliente_nombre='Juan',
        )
        resultado = self.svc.cancelar(reserva.id)
        self.assertFalse(resultado.activo)

    def test_cancelar_reserva_no_existe(self):
        with self.assertRaises(RecursoNoEncontrado):
            self.svc.cancelar(999)

    def test_cancelar_reserva_ya_cancelada(self):
        reserva = self.svc.crear(
            mesas_ids=[self.mesa.id],
            fecha=date(2026, 8, 1),
            hora_inicio='12:00', hora_fin='14:00',
            num_personas=2, cliente_nombre='Juan',
        )
        self.svc.cancelar(reserva.id)
        with self.assertRaises(ReglaNegocioViolada):
            self.svc.cancelar(reserva.id)

    def test_finalizar_reserva_ok(self):
        reserva = self.svc.crear(
            mesas_ids=[self.mesa.id],
            fecha=date(2026, 8, 1),
            hora_inicio='12:00', hora_fin='14:00',
            num_personas=2, cliente_nombre='Juan',
        )
        resultado = self.svc.finalizar(reserva.id)
        self.assertTrue(resultado.finalizada)

    def test_finalizar_reserva_no_existe(self):
        with self.assertRaises(RecursoNoEncontrado):
            self.svc.finalizar(999)

    def test_finalizar_reserva_cancelada(self):
        reserva = self.svc.crear(
            mesas_ids=[self.mesa.id],
            fecha=date(2026, 8, 1),
            hora_inicio='12:00', hora_fin='14:00',
            num_personas=2, cliente_nombre='Juan',
        )
        self.svc.cancelar(reserva.id)
        with self.assertRaises(ReglaNegocioViolada):
            self.svc.finalizar(reserva.id)

    def test_editar_reserva_ok(self):
        reserva = self.svc.crear(
            mesas_ids=[self.mesa.id],
            fecha=date(2026, 8, 1),
            hora_inicio='12:00', hora_fin='14:00',
            num_personas=2, cliente_nombre='Juan',
        )
        editada = self.svc.editar(
            reserva.id,
            mesas_ids=[self.mesa.id],
            fecha=date(2026, 8, 2),
            hora_inicio='13:00', hora_fin='15:00',
            num_personas=3, cliente_nombre='Juan Actualizado',
        )
        self.assertEqual(editada.cliente_nombre, 'Juan Actualizado')
        self.assertEqual(editada.fecha, date(2026, 8, 2))

    def test_editar_reserva_cancelada_lanza_error(self):
        reserva = self.svc.crear(
            mesas_ids=[self.mesa.id],
            fecha=date(2026, 8, 1),
            hora_inicio='12:00', hora_fin='14:00',
            num_personas=2, cliente_nombre='Juan',
        )
        self.svc.cancelar(reserva.id)
        with self.assertRaises(ReglaNegocioViolada):
            self.svc.editar(
                reserva.id,
                mesas_ids=[self.mesa.id],
                fecha=date(2026, 8, 2),
                hora_inicio='13:00', hora_fin='15:00',
                num_personas=2, cliente_nombre='Juan',
            )

    def test_editar_reserva_no_existe(self):
        with self.assertRaises(RecursoNoEncontrado):
            self.svc.editar(
                999,
                mesas_ids=[self.mesa.id],
                fecha=date(2026, 8, 1),
                hora_inicio='12:00', hora_fin='14:00',
                num_personas=2, cliente_nombre='Juan',
            )

    def test_eliminar_reserva_activa_lanza_error(self):
        reserva = self.svc.crear(
            mesas_ids=[self.mesa.id],
            fecha=date(2026, 8, 1),
            hora_inicio='12:00', hora_fin='14:00',
            num_personas=2, cliente_nombre='Juan',
        )
        with self.assertRaises(ReglaNegocioViolada):
            self.svc.eliminar_definitivamente(reserva.id)

    def test_eliminar_reserva_cancelada_ok(self):
        reserva = self.svc.crear(
            mesas_ids=[self.mesa.id],
            fecha=date(2026, 8, 1),
            hora_inicio='12:00', hora_fin='14:00',
            num_personas=2, cliente_nombre='Juan',
        )
        self.svc.cancelar(reserva.id)
        self.svc.eliminar_definitivamente(reserva.id)
        with self.assertRaises(Reserva.DoesNotExist):
            Reserva.objects.get(id=reserva.id)

    def test_eliminar_reserva_no_existe(self):
        with self.assertRaises(RecursoNoEncontrado):
            self.svc.eliminar_definitivamente(999)

    def test_crear_reserva_zonas_diferentes_lanza_error(self):
        mesa2 = Mesa.objects.create(numero=2, capacidad=4, zona='TERRAZA')
        with self.assertRaises(ReglaNegocioViolada):
            self.svc.crear(
                mesas_ids=[self.mesa.id, mesa2.id],
                fecha=date(2026, 8, 1),
                hora_inicio='12:00', hora_fin='14:00',
                num_personas=4, cliente_nombre='Juan',
            )

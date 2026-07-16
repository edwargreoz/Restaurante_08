from decimal import Decimal
from django.test import TestCase
from django.contrib.auth.models import User
from core.excepciones import (
    UnionInvalida, RecursoNoEncontrado, ReglaNegocioViolada,
)
from mesas.models import Mesa, UnionMesa
from mesas.services import MesaService, UnionMesaService
from infraestructura.container import get_container


def _mesa_service():
    return MesaService(mesa_repo=get_container().mesa_repo)


def _union_mesa_service():
    return UnionMesaService(mesa_repo=get_container().mesa_repo)


class MesaServiceTest(TestCase):
    def setUp(self):
        self.svc = _mesa_service()
        self.mesa = Mesa.objects.create(numero=1, capacidad=4, estado='LIBRE')

    def test_cambiar_estado_ok(self):
        resultado = self.svc.cambiar_estado(self.mesa.id, 'OCUPADA')
        self.assertEqual(resultado.estado, 'OCUPADA')

    def test_cambiar_estado_mesa_no_existe(self):
        with self.assertRaises(RecursoNoEncontrado):
            self.svc.cambiar_estado(999, 'OCUPADA')

    def test_marcar_libre_desde_limpieza(self):
        self.mesa.estado = 'LIMPIEZA'
        self.mesa.save()
        resultado = self.svc.marcar_libre(self.mesa.id)
        self.assertEqual(resultado.estado, 'LIBRE')

    def test_marcar_libre_no_limpieza_lanza_error(self):
        self.mesa.estado = 'OCUPADA'
        self.mesa.save()
        with self.assertRaises(ReglaNegocioViolada):
            self.svc.marcar_libre(self.mesa.id)

    def test_marcar_libre_mesa_no_existe(self):
        with self.assertRaises(RecursoNoEncontrado):
            self.svc.marcar_libre(999)


class UnionMesaServiceTest(TestCase):
    def setUp(self):
        self.svc = _union_mesa_service()
        self.mesa1 = Mesa.objects.create(numero=1, capacidad=4, estado='LIBRE')
        self.mesa2 = Mesa.objects.create(numero=2, capacidad=4, estado='LIBRE')

    def test_crear_union_ok(self):
        union = self.svc.crear([self.mesa1.id, self.mesa2.id])
        self.assertTrue(union.activo)
        self.assertEqual(union.mesas.count(), 2)

    def test_crear_union_un_mesa_lanza_error(self):
        with self.assertRaises(UnionInvalida):
            self.svc.crear([self.mesa1.id])

    def test_crear_union_mesa_no_existe(self):
        with self.assertRaises(UnionInvalida):
            self.svc.crear([self.mesa1.id, 999])

    def test_crear_union_mesa_reservada(self):
        self.mesa2.estado = 'RESERVADA'
        self.mesa2.save()
        with self.assertRaises(UnionInvalida):
            self.svc.crear([self.mesa1.id, self.mesa2.id])

    def test_crear_union_zonas_diferentes(self):
        mesa3 = Mesa.objects.create(numero=3, capacidad=4, zona='TERRAZA')
        with self.assertRaises(UnionInvalida):
            self.svc.crear([self.mesa1.id, mesa3.id])

    def test_crear_union_duplicada(self):
        self.svc.crear([self.mesa1.id, self.mesa2.id])
        with self.assertRaises(UnionInvalida):
            self.svc.crear([self.mesa1.id, self.mesa2.id])

    def test_deshacer_union_ok(self):
        usuario = User.objects.create_user(username='mozo', password='test')
        union = self.svc.crear([self.mesa1.id, self.mesa2.id])
        self.svc.deshacer(union.id, usuario)
        union.refresh_from_db()
        self.assertFalse(union.activo)

    def test_deshacer_union_no_existe(self):
        usuario = User.objects.create_user(username='mozo', password='test')
        with self.assertRaises(RecursoNoEncontrado):
            self.svc.deshacer(999, usuario)

    def test_agregar_mesa_ok(self):
        usuario = User.objects.create_user(username='mozo', password='test')
        union = self.svc.crear([self.mesa1.id, self.mesa2.id])
        mesa3 = Mesa.objects.create(numero=3, capacidad=4, estado='LIBRE')
        resultado = self.svc.agregar_mesa(union.id, mesa3.id, usuario)
        self.assertEqual(resultado.mesas.count(), 3)

    def test_agregar_mesa_ya_en_union(self):
        usuario = User.objects.create_user(username='mozo', password='test')
        union = self.svc.crear([self.mesa1.id, self.mesa2.id])
        with self.assertRaises(UnionInvalida):
            self.svc.agregar_mesa(union.id, self.mesa1.id, usuario)

    def test_agregar_mesa_reservada(self):
        usuario = User.objects.create_user(username='mozo', password='test')
        union = self.svc.crear([self.mesa1.id, self.mesa2.id])
        mesa3 = Mesa.objects.create(numero=3, capacidad=4, estado='RESERVADA')
        with self.assertRaises(UnionInvalida):
            self.svc.agregar_mesa(union.id, mesa3.id, usuario)

    def test_agregar_mesa_union_no_existe(self):
        usuario = User.objects.create_user(username='mozo', password='test')
        with self.assertRaises(RecursoNoEncontrado):
            self.svc.agregar_mesa(999, self.mesa1.id, usuario)

    def test_agregar_mesa_no_existe(self):
        usuario = User.objects.create_user(username='mozo', password='test')
        union = self.svc.crear([self.mesa1.id, self.mesa2.id])
        with self.assertRaises(RecursoNoEncontrado):
            self.svc.agregar_mesa(union.id, 999, usuario)

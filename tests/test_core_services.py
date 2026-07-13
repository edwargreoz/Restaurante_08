from decimal import Decimal
from django.test import TestCase
from django.contrib.auth.models import User, Group
from core.services import DashboardService, UsuarioService
from core.excepciones import RecursoNoEncontrado, ReglaNegocioViolada
from mesas.models import Mesa
from caja.models import Caja
from inventario.models import Insumo


class DashboardServiceTest(TestCase):
    def setUp(self):
        self.usuario = User.objects.create_user(username='mozo', password='pass123')
        Mesa.objects.create(numero=1, capacidad=4, estado='LIBRE')
        Mesa.objects.create(numero=2, capacidad=2, estado='OCUPADA')

    def test_datos_mozo(self):
        datos = DashboardService.datos_mozo()
        self.assertEqual(datos['mesas_libres'], 1)
        self.assertEqual(datos['mesas_ocupadas'], 1)

    def test_datos_cajero(self):
        caja = Caja.objects.create(
            turno='MAÑANA', cajero=self.usuario,
            saldo_inicial=Decimal('100'), estado='ABIERTA',
        )
        datos = DashboardService.datos_cajero()
        self.assertEqual(datos['ventas_hoy'], 0)
        self.assertEqual(datos['caja_actual'].id, caja.id)


class UsuarioServiceTest(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(username='admin', password='admin')
        self.usuario = User.objects.create_user(
            username='mozo', password='pass123', first_name='Juan', last_name='Perez'
        )

    def test_obtener_por_id(self):
        user = UsuarioService.obtener_por_id(self.usuario.id)
        self.assertEqual(user.username, 'mozo')

    def test_obtener_por_id_no_existe(self):
        with self.assertRaises(RecursoNoEncontrado):
            UsuarioService.obtener_por_id(999)

    def test_listar_usuarios(self):
        usuarios = UsuarioService.listar_usuarios()
        self.assertEqual(usuarios.count(), 2)

    def test_crear_usuario(self):
        user = UsuarioService.crear('nuevo', 'pass123', grupo_nombre='Mozo')
        self.assertTrue(user.check_password('pass123'))
        self.assertTrue(user.groups.filter(name='Mozo').exists())

    def test_crear_usuario_sin_grupo(self):
        user = UsuarioService.crear('simple', 'pass123')
        self.assertEqual(user.groups.count(), 0)

    def test_actualizar_campos(self):
        user = UsuarioService.actualizar(
            self.usuario.id, self.usuario.id,
            first_name='Pedro', email='pedro@test.com'
        )
        self.assertEqual(user.first_name, 'Pedro')
        self.assertEqual(user.email, 'pedro@test.com')

    def test_actualizar_password(self):
        UsuarioService.actualizar(
            self.usuario.id, self.usuario.id, password='nuevapass'
        )
        self.usuario.refresh_from_db()
        self.assertTrue(self.usuario.check_password('nuevapass'))

    def test_actualizar_rol_admin(self):
        user = UsuarioService.actualizar(
            self.usuario.id, self.usuario.id, rol='Admin'
        )
        user.refresh_from_db()
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_staff)

    def test_actualizar_rol_mozo(self):
        UsuarioService.actualizar(
            self.usuario.id, self.usuario.id, rol='Admin'
        )
        user = UsuarioService.actualizar(
            self.usuario.id, self.usuario.id, rol='Mozo'
        )
        user.refresh_from_db()
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.groups.filter(name='Mozo').exists())

    def test_no_puede_desactivar_self(self):
        with self.assertRaises(ReglaNegocioViolada):
            UsuarioService.actualizar(
                self.admin.id, self.admin.id, is_active=False
            )

    def test_desactivar_usuario(self):
        user = UsuarioService.desactivar(self.usuario.id, self.admin.id)
        self.assertFalse(user.is_active)

    def test_desactivar_self(self):
        with self.assertRaises(ReglaNegocioViolada):
            UsuarioService.desactivar(self.admin.id, self.admin.id)

    def test_desactivar_no_existe(self):
        with self.assertRaises(RecursoNoEncontrado):
            UsuarioService.desactivar(999, self.admin.id)

    def test_actualizar_no_existe(self):
        with self.assertRaises(RecursoNoEncontrado):
            UsuarioService.actualizar(999, self.admin.id, username='x')

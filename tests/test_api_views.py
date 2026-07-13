from decimal import Decimal
from django.test import TestCase, override_settings
from django.contrib.auth.models import User, Group
from rest_framework.test import APIClient
from rest_framework import status

from mesas.models import Mesa, UnionMesa
from menu.models import Categoria, Plato
from inventario.models import Insumo, Receta, RecetaInsumo
from caja.models import Caja, Pago
from pedidos.models import Comanda, LineaComanda
from reservas.models import Reserva


class ApiTestBase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_superuser(
            username='admin', password='admin', first_name='Admin'
        )
        self.mozo_group, _ = Group.objects.get_or_create(name='Mozo')
        self.cajero_group, _ = Group.objects.get_or_create(name='Cajero')
        self.cocinero_group, _ = Group.objects.get_or_create(name='Cocinero')

        self.mozo = User.objects.create_user(username='mozo', password='pass123')
        self.mozo.groups.add(self.mozo_group)
        self.cajero = User.objects.create_user(username='cajero', password='pass123')
        self.cajero.groups.add(self.cajero_group)
        self.cocinero = User.objects.create_user(username='cocinero', password='pass123')
        self.cocinero.groups.add(self.cocinero_group)

        self.mesa = Mesa.objects.create(numero=1, capacidad=4, estado='LIBRE')
        self.categoria = Categoria.objects.create(nombre='Platos', orden_display=1)
        self.insumo = Insumo.objects.create(
            nombre='Aceite', unidad='ML', stock_actual=Decimal('1000'),
            stock_minimo=Decimal('100'),
        )
        self.receta = Receta.objects.create(nombre='Receta Base')
        RecetaInsumo.objects.create(
            receta=self.receta, insumo=self.insumo,
            cantidad_por_porcion=Decimal('50'), unidad='ML',
        )
        self.plato = Plato.objects.create(
            nombre='Lomo Saltado', precio=Decimal('35.00'),
            categoria=self.categoria, receta=self.receta,
        )
        self.caja = Caja.objects.create(
            turno='MAÑANA', cajero=self.cajero,
            saldo_inicial=Decimal('100'), estado='ABIERTA',
        )
        self.comanda = Comanda.objects.create(
            mesa=self.mesa, mozo=self.mozo, estado='LISTA',
        )
        LineaComanda.objects.create(
            comanda=self.comanda, plato=self.plato, cantidad=2,
        )
        self.reserva = Reserva.objects.create(
            mesa=self.mesa, cliente_nombre='Juan', fecha='2026-12-31',
            hora_inicio='19:00', hora_fin='21:00', num_personas=2,
            creado_por=self.mozo,
        )


class PermisoTests(ApiTestBase):
    def test_es_mozo_permiso_superadmin(self):
        request = type('obj', (object,), {'user': self.admin})()
        from interfaces.api.permissions import EsMozo
        self.assertTrue(EsMozo().has_permission(request, None))

    def test_es_mozo_permiso_mozo(self):
        request = type('obj', (object,), {'user': self.mozo})()
        from interfaces.api.permissions import EsMozo
        self.assertTrue(EsMozo().has_permission(request, None))

    def test_es_mozo_permiso_fallido(self):
        request = type('obj', (object,), {'user': self.cajero})()
        from interfaces.api.permissions import EsMozo
        self.assertFalse(EsMozo().has_permission(request, None))

    def test_es_cocinero(self):
        request = type('obj', (object,), {'user': self.cocinero})()
        from interfaces.api.permissions import EsCocinero
        self.assertTrue(EsCocinero().has_permission(request, None))

    def test_es_cajero(self):
        request = type('obj', (object,), {'user': self.cajero})()
        from interfaces.api.permissions import EsCajero
        self.assertTrue(EsCajero().has_permission(request, None))

    def test_es_admin(self):
        request = type('obj', (object,), {'user': self.admin})()
        from interfaces.api.permissions import EsAdmin
        self.assertTrue(EsAdmin().has_permission(request, None))

    def test_es_admin_fallido(self):
        request = type('obj', (object,), {'user': self.mozo})()
        from interfaces.api.permissions import EsAdmin
        self.assertFalse(EsAdmin().has_permission(request, None))


class SerializersTests(ApiTestBase):
    def test_categoria_serializer(self):
        from interfaces.api.serializers import CategoriaSerializer
        s = CategoriaSerializer(self.categoria)
        self.assertIn('nombre', s.data)

    def test_plato_serializer(self):
        from interfaces.api.serializers import PlatoSerializer
        s = PlatoSerializer(self.plato)
        self.assertEqual(s.data['nombre'], 'Lomo Saltado')
        self.assertIn('categoria_nombre', s.data)

    def test_insumo_serializer(self):
        from interfaces.api.serializers import InsumoSerializer
        s = InsumoSerializer(self.insumo)
        self.assertEqual(s.data['nombre'], 'Aceite')

    def test_receta_insumo_serializer(self):
        from interfaces.api.serializers import RecetaInsumoSerializer
        ri = RecetaInsumo.objects.first()
        s = RecetaInsumoSerializer(ri)
        self.assertIn('receta_nombre', s.data)

    def test_receta_serializer(self):
        from interfaces.api.serializers import RecetaSerializer
        s = RecetaSerializer(self.receta)
        self.assertIn('nombre', s.data)

    def test_mesa_serializer(self):
        from interfaces.api.serializers import MesaSerializer
        s = MesaSerializer(self.mesa)
        self.assertIn('numero', s.data)

    def test_linea_comanda_serializer(self):
        from interfaces.api.serializers import LineaComandaSerializer
        linea = LineaComanda.objects.first()
        s = LineaComandaSerializer(linea)
        self.assertIn('subtotal', s.data)
        self.assertIn('nombre_plato', s.data)

    def test_comanda_serializer(self):
        from interfaces.api.serializers import ComandaSerializer
        s = ComandaSerializer(self.comanda)
        self.assertIn('total', s.data)
        self.assertIn('lineas', s.data)

    def test_agregar_plato_serializer(self):
        from interfaces.api.serializers import AgregarPlatoSerializer
        s = AgregarPlatoSerializer(data={'plato_id': 1, 'cantidad': 2})
        self.assertTrue(s.is_valid())

    def test_agregar_platos_request_serializer(self):
        from interfaces.api.serializers import AgregarPlatosRequestSerializer
        s = AgregarPlatosRequestSerializer(
            data={'platos': [{'plato_id': 1, 'cantidad': 1}]}
        )
        self.assertTrue(s.is_valid())

    def test_pagar_request_serializer(self):
        from interfaces.api.serializers import PagarRequestSerializer
        s = PagarRequestSerializer(
            data={'metodo': 'EFECTIVO', 'monto': '50.00'}
        )
        self.assertTrue(s.is_valid())

    def test_cocina_linea_serializer(self):
        from interfaces.api.serializers import CocinaLineaSerializer
        linea = LineaComanda.objects.first()
        linea.estado = 'PENDIENTE'
        linea.save()
        s = CocinaLineaSerializer(linea)
        self.assertIn('tiempo_prep', s.data)

    def test_reserva_serializer(self):
        from interfaces.api.serializers import ReservaSerializer
        s = ReservaSerializer(self.reserva)
        self.assertIn('mesa_numero', s.data)

    def test_reserva_serializer_union(self):
        from interfaces.api.serializers import ReservaSerializer
        m1 = Mesa.objects.create(numero=10, capacidad=2)
        m2 = Mesa.objects.create(numero=11, capacidad=2)
        union = UnionMesa.objects.create(activo=True)
        union.mesas.set([m1, m2])
        r = Reserva.objects.create(
            union_mesa=union, cliente_nombre='Test Union',
            fecha='2026-12-31', hora_inicio='19:00', hora_fin='21:00',
            num_personas=3, creado_por=self.mozo,
        )
        s = ReservaSerializer(r)
        self.assertIsNotNone(s.data.get('union_mesa_nombre'))

    def test_union_mesa_serializer(self):
        from interfaces.api.serializers import UnionMesaSerializer
        union = UnionMesa.objects.create(activo=True)
        union.mesas.add(self.mesa)
        s = UnionMesaSerializer(union)
        self.assertIn('capacidad_total', s.data)


class PaginacionTest(ApiTestBase):
    def test_paginacion(self):
        from interfaces.api.pagination import PaginacionRestaurant
        p = PaginacionRestaurant()
        self.assertEqual(p.page_size, 15)
        self.assertEqual(p.max_page_size, 100)


class FilterTests(ApiTestBase):
    def test_comanda_filter(self):
        from interfaces.api.filters import ComandaFilter
        qs = Comanda.objects.all()
        f = ComandaFilter(data={'estado': 'LISTA'}, queryset=qs)
        self.assertEqual(f.qs.count(), 1)

    def test_plato_filter(self):
        from interfaces.api.filters import PlatoFilter
        qs = Plato.objects.all()
        f = PlatoFilter(data={'disponible': True}, queryset=qs)
        self.assertEqual(f.qs.count(), 1)


class MesaApiTests(ApiTestBase):
    def test_list_mesas(self):
        self.client.force_authenticate(user=self.mozo)
        resp = self.client.get('/api/v1/mesas/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_estado_actual(self):
        self.client.force_authenticate(user=self.mozo)
        resp = self.client.get('/api/v1/mesas/estado_actual/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)


class CategoriaApiTests(ApiTestBase):
    def test_list_categorias(self):
        self.client.force_authenticate(user=self.mozo)
        resp = self.client.get('/api/v1/categorias/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)


class PlatoApiTests(ApiTestBase):
    def test_list_platos(self):
        self.client.force_authenticate(user=self.mozo)
        resp = self.client.get('/api/v1/platos/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_filter_plato_por_categoria(self):
        self.client.force_authenticate(user=self.mozo)
        resp = self.client.get(f'/api/v1/platos/?categoria={self.categoria.id}')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)


class InsumoApiTests(ApiTestBase):
    def test_list_insumos_admin(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.get('/api/v1/insumos/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_list_insumos_no_admin(self):
        self.client.force_authenticate(user=self.mozo)
        resp = self.client.get('/api/v1/insumos/')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


class RecetaApiTests(ApiTestBase):
    def test_list_recetas(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.get('/api/v1/recetas/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)


class RecetaInsumoApiTests(ApiTestBase):
    def test_list_receta_insumos(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.get('/api/v1/recetas-insumo/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)


class ReservaApiTests(ApiTestBase):
    def test_list_reservas(self):
        self.client.force_authenticate(user=self.mozo)
        resp = self.client.get('/api/v1/reservas/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_cancelar_reserva(self):
        self.client.force_authenticate(user=self.mozo)
        resp = self.client.delete(f'/api/v1/reservas/{self.reserva.id}/')
        self.assertIn(resp.status_code, [204, 200])


class UnionMesaApiTests(ApiTestBase):
    def test_list_uniones(self):
        self.client.force_authenticate(user=self.mozo)
        resp = self.client.get('/api/v1/uniones-mesas/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)


class ComandaApiTests(ApiTestBase):
    def test_list_comandas(self):
        self.client.force_authenticate(user=self.mozo)
        resp = self.client.get('/api/v1/comandas/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_abrir_comanda(self):
        self.client.force_authenticate(user=self.mozo)
        resp = self.client.post(
            '/api/v1/comandas/abrir/',
            {'mesa_id': self.mesa.id}, format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_abrir_comanda_sin_mesa(self):
        self.client.force_authenticate(user=self.mozo)
        resp = self.client.post('/api/v1/comandas/abrir/', {}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_agregar_platos(self):
        self.client.force_authenticate(user=self.mozo)
        comanda = Comanda.objects.create(
            mesa=self.mesa, mozo=self.mozo, estado='ABIERTA',
        )
        resp = self.client.post(
            f'/api/v1/comandas/{comanda.id}/agregar_platos/',
            {'platos': [{'plato_id': self.plato.id, 'cantidad': 1}]},
            format='json',
        )
        self.assertIn(resp.status_code, [200, 201])

    def test_pagar_comanda(self):
        self.client.force_authenticate(user=self.mozo)
        resp = self.client.post(
            f'/api/v1/comandas/{self.comanda.id}/pagar/',
            {'metodo': 'EFECTIVO', 'monto': '70.00', 'vuelto': 0},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_pagar_split(self):
        self.client.force_authenticate(user=self.mozo)
        resp = self.client.post(
            f'/api/v1/comandas/{self.comanda.id}/pagar_split/',
            {'pagos': [
                {'metodo': 'EFECTIVO', 'monto': '35.00'},
                {'metodo': 'YAPE', 'monto': '35.00'},
            ]},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_anular_comanda(self):
        self.client.force_authenticate(user=self.mozo)
        comanda = Comanda.objects.create(
            mesa=self.mesa, mozo=self.mozo, estado='ABIERTA',
        )
        resp = self.client.post(
            f'/api/v1/comandas/{comanda.id}/anular/', format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_filter_comandas(self):
        self.client.force_authenticate(user=self.mozo)
        resp = self.client.get('/api/v1/comandas/?estado=LISTA')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)


class LineaComandaApiTests(ApiTestBase):
    def test_list_lineas(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.get('/api/v1/lineas-comanda/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_enviar_cocina(self):
        self.client.force_authenticate(user=self.cocinero)
        linea = LineaComanda.objects.first()
        linea.estado = 'PENDIENTE'
        linea.save()
        resp = self.client.post(
            f'/api/v1/lineas-comanda/{linea.id}/enviar_cocina/',
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_marcar_listo(self):
        self.client.force_authenticate(user=self.cocinero)
        linea = LineaComanda.objects.first()
        linea.estado = 'EN_PREP'
        linea.save()
        resp = self.client.patch(
            f'/api/v1/lineas-comanda/{linea.id}/marcar_listo/',
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)


class CocinaApiTests(ApiTestBase):
    def test_list_cocina(self):
        self.client.force_authenticate(user=self.cocinero)
        resp = self.client.get('/api/v1/cocina/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)


class ReportesApiTests(ApiTestBase):
    def test_ventas_turno(self):
        self.client.force_authenticate(user=self.cajero)
        resp = self.client.get('/api/v1/reportes/ventas_turno/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

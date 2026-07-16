
from django.db.models import Sum, F
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from mesas.models import Mesa
from pedidos.models import Comanda
from inventario.models import Insumo
from caja.models import Caja, Pago
from django.contrib.auth.models import User
from core.excepciones import RecursoNoEncontrado, ReglaNegocioViolada


class DashboardService:
    @staticmethod
    def datos_mozo():
        return {
            'mesas_libres': Mesa.activos.filter(estado='LIBRE').count(),
            'mesas_ocupadas': Mesa.activos.filter(estado='OCUPADA').count(),
            'comandas_activas': Comanda.objects.filter(
                estado__in=['ABIERTA', 'EN_PREPARACION']
            ).count(),
            'alertas_stock': Insumo.objects.filter(
                stock_actual__lt=F('stock_minimo')
            ).count(),
            'ultimas_comandas': Comanda.objects.filter(
                estado__in=['ABIERTA', 'EN_PREPARACION']
            ).select_related('mesa', 'mozo').order_by('-fecha_apertura')[:5],
            'alertas_detalle': Insumo.objects.filter(
                stock_actual__lt=F('stock_minimo')
            )[:5],
        }

    @staticmethod
    def datos_cajero():
        hoy = timezone.now().date()
        return {
            'ventas_hoy': Pago.objects.filter(
                fecha__date__gte=hoy,
                fecha__date__lt=hoy + timedelta(days=1)
            ).aggregate(total=Sum('monto'))['total'] or 0,
            'caja_actual': Caja.objects.filter(estado='ABIERTA').first(),
        }


class UsuarioService:
    @staticmethod
    def obtener_por_id(user_id: int) -> User:
        user = User.objects.filter(id=user_id).first()
        if not user:
            raise RecursoNoEncontrado('Usuario no encontrado')
        return user
    @staticmethod
    def listar_usuarios():
        return User.objects.prefetch_related('groups').order_by('-is_active', 'username')

    @staticmethod
    @transaction.atomic
    def crear(username, password, grupo_nombre=None, **extra) -> User:
        from django.contrib.auth.models import Group
        user = User.objects.create_user(
            username=username, password=password, **extra
        )
        if grupo_nombre:
            grupo, _ = Group.objects.get_or_create(name=grupo_nombre)
            user.groups.add(grupo)
        return user

    @staticmethod
    @transaction.atomic
    def actualizar(user_id: int, solicitante_id: int, **campos) -> User:
        from django.contrib.auth.models import Group
        user = UsuarioService.obtener_por_id(user_id)
        is_active = campos.get('is_active', user.is_active)
        if not is_active and user_id == solicitante_id:
            raise ReglaNegocioViolada('No puedes desactivar tu propio usuario')
        for attr in ('username', 'first_name', 'last_name', 'email'):
            if attr in campos:
                setattr(user, attr, campos[attr])
        user.is_active = is_active
        password = campos.get('password')
        if password:
            user.set_password(password)
        rol = campos.get('rol')
        if rol == 'Admin':
            user.is_superuser = True
            user.is_staff = True
        else:
            user.is_superuser = False
            user.is_staff = False
        user.save(update_fields=[
            'username', 'first_name', 'last_name', 'email',
            'is_active', 'is_superuser', 'is_staff', 'password',
        ])
        if rol is not None:
            user.groups.clear()
            if rol != 'Admin':
                grupo, _ = Group.objects.get_or_create(name=rol)
                user.groups.add(grupo)
        return user

    @staticmethod
    def desactivar(user_id: int, solicitante_id: int) -> User:
        if user_id == solicitante_id:
            raise ReglaNegocioViolada('No puedes desactivarte a ti mismo')
        user = User.objects.filter(id=user_id).first()
        if not user:
            raise RecursoNoEncontrado('Usuario no encontrado')
        user.is_active = False
        user.save(update_fields=['is_active'])
        return user

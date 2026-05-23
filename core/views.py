
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required

#Raiza modificó dashboard_view y añadio los imports de mesa, comanda e insumo
from mesas.models import Mesa
from pedidos.models import Comanda
from inventario.models import Insumo
from django.db import models
#Raiza
from django.utils import timezone #para mostrar fecha y hora en el dashboard
from datetime import timedelta #para calcular pedidos del dia
from caja.models import Caja,Pago #para mostrar ingresos del dia en el dashboard


def login_view(request):
    if request.user.is_authenticated:
        if request.user.groups.filter(name='Cocinero').exists() and not request.user.is_superuser:
            return redirect('kds_panel')
        return redirect('dashboard')
    if request.method == 'POST':
        # Obtener credenciales del formulario
        username = request.POST.get('username')
        password = request.POST.get('password')

        # Autenticar usuario (Sesion 04 - auth.authenticate)
        user = authenticate(request, username=username, password=password)

        if user is not None:
            # Iniciar sesion si las credenciales son correctas
            login(request, user)
            if user.groups.filter(name='Cocinero').exists() and not user.is_superuser:
                return redirect('kds_panel')
            return redirect('dashboard')
        else:
            # Error: credenciales invalidas
            return render(request, 'auth/login.html', {
                'error': 'Usuario o contrasena incorrectos'
            })

    # GET: mostrar formulario de login
    return render(request, 'auth/login.html')


@login_required
def dashboard_view(request):
    es_mozo = request.user.is_superuser or request.user.groups.filter(name='Mozo').exists()
    es_cajero = request.user.is_superuser or request.user.groups.filter(name='Cajero').exists()

    if not es_mozo and not es_cajero:
        return redirect('kds_panel')

    context = {}

    if es_mozo:
        context['mesas_libres'] = Mesa.objects.filter(estado='LIBRE').count()
        context['mesas_ocupadas'] = Mesa.objects.filter(estado='OCUPADA').count()
        context['comandas_activas'] = Comanda.objects.filter(
            estado__in=['ABIERTA', 'EN_PREPARACION']
        ).count()
        context['alertas_stock'] = Insumo.objects.filter(
            stock_actual__lt=models.F('stock_minimo')
        ).count()
        context['ultimas_comandas'] = Comanda.objects.filter(
            estado__in=['ABIERTA', 'EN_PREPARACION']
        ).select_related('mesa', 'mozo').order_by('-fecha_apertura')[:5]
        context['alertas_detalle'] = Insumo.objects.filter(
            stock_actual__lt=models.F('stock_minimo')
        )[:5]

    if es_cajero:
        hoy = timezone.now().date()
        context['ventas_hoy'] = Pago.objects.filter(
            fecha__date__gte=hoy,
            fecha__date__lt=hoy + timedelta(days=1)
        ).aggregate(total=models.Sum('monto'))['total'] or 0
        context['caja_actual'] = Caja.objects.filter(estado='ABIERTA').first()

    return render(request, 'core/dashboard.html', context)


def logout_view(request):
    logout(request)
    return redirect('login')

# --- GESTIÓN DE USUARIOS ---
from django.contrib.auth.models import User
from django.contrib import messages
from django.shortcuts import get_object_or_404
from core.rol_utils import es_admin
from django.contrib.auth.decorators import user_passes_test
from .forms import UsuarioForm

@login_required
@user_passes_test(es_admin)
def lista_usuarios(request):
    usuarios = User.objects.all().order_by('-is_active', 'username')
    return render(request, 'core/usuarios/lista_usuarios.html', {'usuarios': usuarios})

@login_required
@user_passes_test(es_admin)
def crear_usuario(request):
    if request.method == 'POST':
        form = UsuarioForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Usuario creado correctamente.')
            return redirect('lista_usuarios')
        else:
            messages.error(request, 'Error al crear el usuario. Por favor verifica los datos.')
    else:
        form = UsuarioForm()
    
    return render(request, 'core/usuarios/form_usuario.html', {
        'form': form,
        'titulo': 'Crear Nuevo Usuario'
    })

@login_required
@user_passes_test(es_admin)
def editar_usuario(request, user_id):
    usuario = get_object_or_404(User, id=user_id)

    if request.method == 'POST':
        form = UsuarioForm(request.POST, instance=usuario)
        if form.is_valid():
            if usuario.id == request.user.id and form.cleaned_data.get('is_active') is False:
                messages.error(request, 'No puedes desactivar tu propio usuario.')
            else:
                form.save()
                messages.success(request, 'Usuario actualizado correctamente.')
                if usuario.id == request.user.id:
                    return redirect('dashboard')
                return redirect('lista_usuarios')
        else:
            messages.error(request, 'Error al actualizar el usuario.')
    else:
        form = UsuarioForm(instance=usuario)

    return render(request, 'core/usuarios/form_usuario.html', {
        'form': form,
        'titulo': 'Editar Usuario',
        'usuario': usuario
    })

@login_required
@user_passes_test(es_admin)
def eliminar_usuario(request, user_id):
    usuario = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        if usuario.id == request.user.id:
            messages.error(request, 'No puedes desactivar tu propio usuario.')
            return redirect('lista_usuarios')
        usuario.is_active = False
        usuario.save()
        messages.success(request, f'El usuario {usuario.username} ha sido desactivado.')
        return redirect('lista_usuarios')

    return redirect('lista_usuarios')

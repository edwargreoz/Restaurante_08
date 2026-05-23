
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
            return redirect('dashboard')
        else:
            # Error: credenciales invalidas
            return render(request, 'auth/login.html', {
                'error': 'Usuario o contrasena incorrectos'
            })

    # GET: mostrar formulario de login
    return render(request, 'auth/login.html')


#segunda modificación by raiza :
@login_required
def dashboard_view(request):
    mesas_libres = Mesa.objects.filter(estado='LIBRE').count()
    mesas_ocupadas = Mesa.objects.filter(estado='OCUPADA').count()
    comandas_activas = Comanda.objects.filter(estado__in=['ABIERTA', 'EN_PREPARACION']).count()
    alertas_stock = Insumo.objects.filter(stock_actual__lt=models.F('stock_minimo')).count()
    
    hoy=timezone.now().date()
    manana=hoy+timedelta(days=1)
    ventas_hoy=Pago.objects.filter(
        fecha__date__gte=hoy,
        fecha__date__lt=manana
    ).aggregate(total=models.Sum('monto'))['total'] or 0 #si no hay ventas, total sera None, por eso usamos 'or 0' para mostrar 0 en vez de None

    
    caja_actual=Caja.objects.filter(estado='ABIERTA').first()

    ultimas_comandas=Comanda.objects.filter(
        estado__in=['ABIERTA', 'EN_PREPARACION']
    ).select_related('mesa', 'mozo').order_by('-fecha_apertura')[:5] #mostrar las 5 comandas mas recientes

    alertas_detalle=Insumo.objects.filter(
        stock_actual__lt=models.F('stock_minimo')
    )[:5] #mostrar solo 5 alertas de stock

    context = {
        'mesas_libres': mesas_libres,
        'mesas_ocupadas': mesas_ocupadas,
        'comandas_activas': comandas_activas,
        'alertas_stock': alertas_stock,
        
        'ventas_hoy': ventas_hoy,
        'caja_actual': caja_actual,
        'ultimas_comandas': ultimas_comandas,
        'alertas_detalle': alertas_detalle,
        
    }
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
            form.save()
            messages.success(request, 'Usuario actualizado correctamente.')
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
        # Soft delete (Desactivar)
        usuario.is_active = False
        usuario.save()
        messages.success(request, f'El usuario {usuario.username} ha sido desactivado.')
        return redirect('lista_usuarios')
        
    return redirect('lista_usuarios')

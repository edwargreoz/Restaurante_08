
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from core.rol_utils import es_admin
from core.excepciones import RecursoNoEncontrado, ReglaNegocioViolada
from .forms import UsuarioForm
from .services import DashboardService, UsuarioService
from django.contrib.auth.decorators import user_passes_test


def login_view(request):
    if request.user.is_authenticated:
        if request.user.groups.filter(name='Cocinero').exists() and not request.user.is_superuser:
            return redirect('kds_panel')
        return redirect('dashboard')
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            if user.groups.filter(name='Cocinero').exists() and not user.is_superuser:
                return redirect('kds_panel')
            return redirect('dashboard')
        else:
            return render(request, 'auth/login.html', {
                'error': 'Usuario o contrasena incorrectos'
            })
    return render(request, 'auth/login.html')


@login_required
def dashboard_view(request):
    es_mozo = request.user.is_superuser or request.user.groups.filter(name='Mozo').exists()
    es_cajero = request.user.is_superuser or request.user.groups.filter(name='Cajero').exists()

    if not es_mozo and not es_cajero:
        return redirect('kds_panel')

    context = {}

    if es_mozo:
        context.update(DashboardService.datos_mozo())

    if es_cajero:
        context.update(DashboardService.datos_cajero())

    return render(request, 'core/dashboard.html', context)


def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
@user_passes_test(es_admin)
def lista_usuarios(request):
    usuarios = UsuarioService.listar_usuarios()
    return render(request, 'core/usuarios/lista_usuarios.html', {'usuarios': usuarios})

@login_required
@user_passes_test(es_admin)
def crear_usuario(request):
    if request.method == 'POST':
        form = UsuarioForm(request.POST)
        if form.is_valid():
            UsuarioService.crear(
                username=form.cleaned_data['username'],
                password=form.cleaned_data['password1'],
                email=form.cleaned_data.get('email', ''),
            )
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
    if request.method == 'POST':
        try:
            UsuarioService.desactivar(user_id, request.user.id)
            messages.success(request, 'Usuario desactivado.')
        except (ReglaNegocioViolada, RecursoNoEncontrado) as e:
            messages.error(request, str(e))
    return redirect('lista_usuarios')

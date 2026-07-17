
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from core.rol_utils import es_admin
from core.excepciones import RecursoNoEncontrado, ReglaNegocioViolada
from .forms import UsuarioForm
from infraestructura.container import get_container
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
    es_mozo_grupo = request.user.is_superuser or request.user.groups.filter(name='Mozo').exists()
    es_cajero_grupo = request.user.is_superuser or request.user.groups.filter(name='Cajero').exists()
    if not es_mozo_grupo and not es_cajero_grupo:
        return redirect('kds_panel')

    container = get_container()
    context = {}

    if es_mozo_grupo:
        context.update(container.dashboard_service.datos_mozo())

    if es_cajero_grupo:
        context.update(container.dashboard_service.datos_cajero())

    return render(request, 'core/dashboard.html', context)


def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
@user_passes_test(es_admin)
def lista_usuarios(request):
    container = get_container()
    usuarios = container.usuario_service.listar_usuarios()
    return render(request, 'core/usuarios/lista_usuarios.html', {'usuarios': usuarios})

@login_required
@user_passes_test(es_admin)
def crear_usuario(request):
    if request.method == 'POST':
        form = UsuarioForm(request.POST)
        if form.is_valid():
            container = get_container()
            container.usuario_service.crear(
                username=form.cleaned_data['username'],
                password=form.cleaned_data['password'],
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
    container = get_container()
    try:
        usuario = container.usuario_service.obtener_por_id(user_id)
    except RecursoNoEncontrado:
        messages.error(request, 'Usuario no encontrado')
        return redirect('lista_usuarios')

    user_orm = User.objects.get(id=user_id)

    if request.method == 'POST':
        form = UsuarioForm(request.POST, instance=user_orm)
        if form.is_valid():
            try:
                container.usuario_service.actualizar(
                    user_id=user_id,
                    solicitante_id=request.user.id,
                    **form.cleaned_data
                )
                messages.success(request, 'Usuario actualizado correctamente.')
                if usuario.id == request.user.id:
                    return redirect('dashboard')
                return redirect('lista_usuarios')
            except (ReglaNegocioViolada, RecursoNoEncontrado) as e:
                messages.error(request, str(e))
        else:
            messages.error(request, 'Error al actualizar el usuario.')
    else:
        form = UsuarioForm(instance=user_orm)

    return render(request, 'core/usuarios/form_usuario.html', {
        'form': form,
        'titulo': 'Editar Usuario',
        'usuario': usuario
    })

@login_required
@user_passes_test(es_admin)
def eliminar_usuario(request, user_id):
    if request.method == 'POST':
        container = get_container()
        try:
            container.usuario_service.desactivar(user_id, request.user.id)
            messages.success(request, 'Usuario desactivado.')
        except (ReglaNegocioViolada, RecursoNoEncontrado) as e:
            messages.error(request, str(e))
    return redirect('lista_usuarios')

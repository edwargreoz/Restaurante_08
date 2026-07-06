
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from core.rol_utils import es_admin
from core.excepciones import RecursoNoEncontrado
from inventario.models import Receta
from menu.models import Categoria, Plato
from .services import CategoriaService, PlatoService

@login_required
def catalogo_platos(request):
    categorias = CategoriaService.listar_categorias()
    return render(request, 'menu/catalogo_platos.html',
                {'categorias': categorias})

@login_required
@user_passes_test(es_admin)
def gestion_menu(request):
    categorias = CategoriaService.listar_categorias()
    recetas = Receta.objects.all()
    return render(request, 'menu/gestion_menu.html', {
        'categorias': categorias,
        'recetas': recetas,
    })

@login_required
@user_passes_test(es_admin)
def crear_categoria(request):
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        if nombre:
            CategoriaService.crear(nombre=nombre)
            messages.success(request, 'Categoria creada')
        else:
            messages.error(request, 'El nombre es obligatorio')
    return redirect('gestion_menu')

@login_required
@user_passes_test(es_admin)
def crear_plato(request):
    if request.method == 'POST':
        categoria_id = request.POST.get('categoria')
        receta_id = request.POST.get('receta')
        if not categoria_id:
            messages.error(request, 'Debe seleccionar una categoría')
            return redirect('gestion_menu')
        if not receta_id:
            messages.error(request, 'Debe seleccionar una receta para el plato')
            return redirect('gestion_menu')
        try:
            PlatoService.crear(
                nombre=request.POST.get('nombre'),
                precio=request.POST.get('precio'),
                categoria_id=categoria_id,
                receta_id=receta_id,
                descripcion=request.POST.get('descripcion', ''),
                disponible=request.POST.get('disponible') == 'on',
                imagen=request.FILES.get('imagen'),
            )
            messages.success(request, 'Plato creado')
        except RecursoNoEncontrado as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
    return redirect('gestion_menu')

@login_required
@user_passes_test(es_admin)
def editar_plato(request, plato_id):
    try:
        plato = Plato.objects.get(id=plato_id)
    except Plato.DoesNotExist:
        messages.error(request, 'Plato no encontrado')
        return redirect('gestion_menu')

    if request.method == 'POST':
        try:
            PlatoService.actualizar(
                plato_id,
                nombre=request.POST.get('nombre', plato.nombre),
                precio=request.POST.get('precio', plato.precio),
                descripcion=request.POST.get('descripcion', ''),
                disponible=request.POST.get('disponible') == 'on',
                categoria=get_object_or_404(Categoria, id=request.POST.get('categoria')),
                imagen=request.FILES.get('imagen'),
            )
            messages.success(request, 'Plato actualizado')
            return redirect('gestion_menu')
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
    categorias = Categoria.objects.all()
    return render(request, 'menu/gestion_menu.html', {
        'editar': plato, 'categorias': categorias
    })

@login_required
@user_passes_test(es_admin)
def eliminar_plato(request, plato_id):
    if request.method == 'POST':
        try:
            PlatoService.eliminar(plato_id)
            messages.success(request, 'Plato eliminado')
        except RecursoNoEncontrado:
            messages.error(request, 'Plato no encontrado')
    return redirect('gestion_menu')

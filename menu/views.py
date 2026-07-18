
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from core.rol_utils import es_admin, es_cualquier_rol
from core.excepciones import RecursoNoEncontrado, ReglaNegocioViolada
from infraestructura.container import get_container
from menu.models import Plato as PlatoModel



@login_required
@user_passes_test(es_cualquier_rol)
def catalogo_platos(request):
    container = get_container()
    categorias = container.categoria_service.listar_categorias()
    return render(request, 'menu/catalogo_platos.html',
                {'categorias': categorias})

@login_required
@user_passes_test(es_admin)
def gestion_menu(request):
    container = get_container()
    categorias = container.categoria_service.listar_categorias()
    recetas = container.receta_service.listar_recetas()
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
            container = get_container()
            container.categoria_service.crear(nombre=nombre)
            messages.success(request, 'Categoria creada')
        else:
            messages.error(request, 'El nombre es obligatorio')
    return redirect('gestion_menu')

@login_required
@user_passes_test(es_admin)
def crear_plato(request):
    if request.method == 'POST':
        container = get_container()
        categoria_id = request.POST.get('categoria')
        receta_id = request.POST.get('receta')
        if not categoria_id:
            messages.error(request, 'Debe seleccionar una categoría')
            return redirect('gestion_menu')
        if not receta_id:
            messages.error(request, 'Debe seleccionar una receta para el plato')
            return redirect('gestion_menu')
        try:
            container.plato_service.crear(
                nombre=request.POST.get('nombre'),
                precio=request.POST.get('precio'),
                categoria_id=categoria_id,
                receta_id=receta_id,
                descripcion=request.POST.get('descripcion', ''),
                disponible=request.POST.get('disponible') == 'on',
            )
            imagen = request.FILES.get('imagen')
            if imagen:
                plato_creado = PlatoModel.objects.order_by('-id').first()
                if plato_creado:
                    plato_creado.imagen = imagen
                    plato_creado.save(update_fields=['imagen'])
            messages.success(request, 'Plato creado')
        except (RecursoNoEncontrado, ReglaNegocioViolada) as e:
            messages.error(request, str(e))
    return redirect('gestion_menu')

@login_required
@user_passes_test(es_admin)
def editar_plato(request, plato_id):
    container = get_container()
    try:
        plato = container.plato_service.obtener_por_id(plato_id)
    except RecursoNoEncontrado:
        messages.error(request, 'Plato no encontrado')
        return redirect('gestion_menu')

    if request.method == 'POST':
        try:
            container.plato_service.actualizar(
                plato_id,
                nombre=request.POST.get('nombre', plato.nombre),
                precio=request.POST.get('precio', plato.precio),
                descripcion=request.POST.get('descripcion', ''),
                disponible=request.POST.get('disponible') == 'on',
                categoria_id=request.POST.get('categoria'),            )
            imagen = request.FILES.get('imagen')
            if imagen:
                p = PlatoModel.objects.get(id=plato_id)
                p.imagen = imagen
                p.save(update_fields=['imagen'])
            messages.success(request, 'Plato actualizado')
            return redirect('gestion_menu')
        except (RecursoNoEncontrado, ReglaNegocioViolada) as e:
            messages.error(request, str(e))
    categorias = container.categoria_service.listar_categorias()
    return render(request, 'menu/gestion_menu.html', {
        'editar': plato, 'categorias': categorias
    })

@login_required
@user_passes_test(es_admin)
def eliminar_plato(request, plato_id):
    if request.method == 'POST':
        container = get_container()
        try:
            container.plato_service.eliminar(plato_id)
            messages.success(request, 'Plato eliminado')
        except RecursoNoEncontrado:
            messages.error(request, 'Plato no encontrado')
    return redirect('gestion_menu')

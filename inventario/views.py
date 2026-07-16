
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from core.rol_utils import es_admin, es_mozo
from core.excepciones import RecursoNoEncontrado, ReglaNegocioViolada
from .models import Insumo
from infraestructura.container import get_container


@login_required
@user_passes_test(es_mozo)
def lista_insumos(request):
    container = get_container()
    insumos = container.insumo_service.listar_insumos()
    return render(request, 'inventario/lista_insumos.html', {
        'insumos': insumos,
        'es_admin': es_admin(request.user)
    })

@login_required
@user_passes_test(es_admin)
def gestion_insumos(request):
    container = get_container()
    insumos = container.insumo_service.listar_insumos()
    return render(request, 'inventario/gestion_insumos.html', {'insumos': insumos})

@login_required
@user_passes_test(es_admin)
def crear_insumo(request):
    if request.method == 'POST':
        try:
            container = get_container()
            container.insumo_service.crear(
                nombre=request.POST.get('nombre'),
                unidad=request.POST.get('unidad'),
                stock_actual=request.POST.get('stock_actual', 0),
                stock_minimo=request.POST.get('stock_minimo', 0),
                costo_unitario=request.POST.get('costo_unitario', 0),
            )
            messages.success(request, 'Insumo creado')
        except (RecursoNoEncontrado, ReglaNegocioViolada) as e:
            messages.error(request, str(e))
    return redirect('gestion_insumos')

@login_required
@user_passes_test(es_admin)
def editar_insumo(request, insumo_id):
    container = get_container()
    try:
        insumo = container.insumo_service.obtener_por_id(insumo_id)
    except RecursoNoEncontrado:
        messages.error(request, 'Insumo no encontrado')
        return redirect('gestion_insumos')

    if request.method == 'POST':
        try:
            container.insumo_service.actualizar(
                insumo_id,
                nombre=request.POST.get('nombre', insumo.nombre),
                unidad=request.POST.get('unidad', insumo.unidad),
                stock_actual=request.POST.get('stock_actual', insumo.stock_actual),
                stock_minimo=request.POST.get('stock_minimo', insumo.stock_minimo),
                costo_unitario=request.POST.get('costo_unitario', insumo.costo_unitario),
            )
            messages.success(request, 'Insumo actualizado')
            return redirect('gestion_insumos')
        except (RecursoNoEncontrado, ReglaNegocioViolada) as e:
            messages.error(request, str(e))
    return render(request, 'inventario/gestion_insumos.html', {
        'editar': insumo,
        'insumos': container.insumo_service.listar_insumos(),
    })

@login_required
@user_passes_test(es_admin)
def eliminar_insumo(request, insumo_id):
    if request.method == 'POST':
        try:
            container = get_container()
            container.insumo_service.eliminar(insumo_id)
            messages.success(request, 'Insumo eliminado')
        except RecursoNoEncontrado:
            messages.error(request, 'Insumo no encontrado')
    return redirect('gestion_insumos')

@login_required
@user_passes_test(es_admin)
def lista_recetas(request):
    container = get_container()
    recetas = container.receta_service.listar_recetas()
    return render(request, 'inventario/lista_recetas.html', {'recetas': recetas})

@login_required
@user_passes_test(es_admin)
def crear_receta(request):
    container = get_container()
    if request.method == 'POST':
        nombre_receta = request.POST.get('nombre_receta')
        if not nombre_receta:
            messages.error(request, 'El nombre de la receta es obligatorio')
            return redirect('crear_receta')
        insumos_ids = request.POST.getlist('insumos[]')
        cantidades = request.POST.getlist('cantidades[]')
        unidades_list = request.POST.getlist('unidades[]')
        if not insumos_ids:
            messages.error(request, 'Debe agregar al menos un insumo')
            return redirect('crear_receta')
        try:
            insumos_data = []
            for insumo_id, cantidad, unidad in zip(insumos_ids, cantidades, unidades_list):
                if not insumo_id or not cantidad:
                    continue
                insumos_data.append({
                    'insumo_id': insumo_id,
                    'cantidad': cantidad,
                    'unidad': unidad,
                })
            container.receta_service.crear(nombre_receta, insumos_data)
            messages.success(request, f'Receta "{nombre_receta}" creada')
        except (RecursoNoEncontrado, ReglaNegocioViolada) as e:
            messages.error(request, str(e))
        return redirect('lista_recetas')
    insumos = container.insumo_service.listar_insumos()
    return render(request, 'inventario/crear_receta.html', {
        'insumos': insumos,
        'unidades': Insumo.UNIDADES,
    })

@login_required
@user_passes_test(es_admin)
def editar_receta(request, receta_id):
    container = get_container()
    try:
        receta = container.receta_service.obtener_por_id(receta_id)
    except RecursoNoEncontrado:
        messages.error(request, 'Receta no encontrada')
        return redirect('lista_recetas')

    if request.method == 'POST':
        try:
            insumos_data = None
            insumos_ids = request.POST.getlist('insumos[]')
            if insumos_ids:
                cantidades = request.POST.getlist('cantidades[]')
                unidades_list = request.POST.getlist('unidades[]')
                insumos_data = []
                for insumo_id, cantidad, unidad in zip(insumos_ids, cantidades, unidades_list):
                    if not insumo_id or not cantidad:
                        continue
                    insumos_data.append({
                        'insumo_id': insumo_id,
                        'cantidad': cantidad,
                        'unidad': unidad,
                    })
            container.receta_service.actualizar(
                receta_id,
                nombre=request.POST.get('nombre_receta'),
                insumos_data=insumos_data,
            )
            messages.success(request, 'Receta actualizada')
        except (RecursoNoEncontrado, ReglaNegocioViolada) as e:
            messages.error(request, str(e))
        return redirect('lista_recetas')
    insumos = container.insumo_service.listar_insumos()
    return render(request, 'inventario/crear_receta.html', {
        'editar': receta,
        'insumos': insumos,
        'unidades': Insumo.UNIDADES,
    })

@login_required
@user_passes_test(es_admin)
def eliminar_receta(request, receta_insumo_id):
    if request.method == 'POST':
        try:
            container = get_container()
            container.receta_service.eliminar_insumo(receta_insumo_id)
            messages.success(request, 'Insumo eliminado de la receta')
        except RecursoNoEncontrado:
            messages.error(request, 'Insumo de receta no encontrado')
    return redirect('lista_recetas')

@login_required
@user_passes_test(es_admin)
def eliminar_receta_completa(request, receta_id):
    if request.method == 'POST':
        try:
            container = get_container()
            container.receta_service.eliminar(receta_id)
            messages.success(request, 'Receta eliminada')
        except RecursoNoEncontrado:
            messages.error(request, 'Receta no encontrada')
    return redirect('lista_recetas')

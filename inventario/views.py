
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
        except Exception:
            messages.error(request, 'No se puede eliminar: tiene registros asociados (movimientos, conversiones o presentaciones).')
    return redirect('gestion_insumos')

@login_required
@user_passes_test(es_admin)
def lista_recetas(request):
    container = get_container()
    recetas = container.receta_service.listar_recetas()
    receta_insumos = container.receta_service.listar_receta_insumos()
    insumos = container.insumo_service.listar_insumos()
    unidades_cocina = container.unidad_cocina_service.listar()
    insumos_dict = {i.id: i for i in insumos}
    uc_dict = {u.id: u for u in unidades_cocina}
    ri_por_receta = {}
    for ri in receta_insumos:
        if ri.receta_id not in ri_por_receta:
            ri_por_receta[ri.receta_id] = []
        ri.insumo_obj = insumos_dict.get(ri.insumo_id)
        ri.unidad_cocina_obj = uc_dict.get(ri.unidad_cocina_id) if ri.unidad_cocina_id else None
        ri_por_receta[ri.receta_id].append(ri)
    for receta in recetas:
        receta.insumos = ri_por_receta.get(receta.id, [])
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
        unidades_cocina_list = request.POST.getlist('unidades_cocina[]')
        if not insumos_ids:
            messages.error(request, 'Debe agregar al menos un insumo')
            return redirect('crear_receta')
        try:
            insumos_data = []
            for i, (insumo_id, cantidad, unidad) in enumerate(zip(insumos_ids, cantidades, unidades_list)):
                if not insumo_id or not cantidad:
                    continue
                uc_id = unidades_cocina_list[i] if i < len(unidades_cocina_list) else None
                item = {
                    'insumo_id': insumo_id,
                    'cantidad': cantidad,
                    'unidad': unidad,
                }
                if uc_id:
                    item['unidad_cocina_id'] = int(uc_id)
                insumos_data.append(item)
            container.receta_service.crear(nombre_receta, insumos_data)
            messages.success(request, f'Receta "{nombre_receta}" creada')
        except (RecursoNoEncontrado, ReglaNegocioViolada) as e:
            messages.error(request, str(e))
        return redirect('lista_recetas')
    insumos = container.insumo_service.listar_insumos()
    unidades_cocina = container.unidad_cocina_service.listar()
    return render(request, 'inventario/crear_receta.html', {
        'insumos': insumos,
        'unidades': Insumo.UNIDADES,
        'unidades_cocina': unidades_cocina,
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
                unidades_cocina_list = request.POST.getlist('unidades_cocina[]')
                insumos_data = []
                for i, (insumo_id, cantidad, unidad) in enumerate(zip(insumos_ids, cantidades, unidades_list)):
                    if not insumo_id or not cantidad:
                        continue
                    uc_id = unidades_cocina_list[i] if i < len(unidades_cocina_list) else None
                    item = {
                        'insumo_id': insumo_id,
                        'cantidad': cantidad,
                        'unidad': unidad,
                    }
                    if uc_id:
                        item['unidad_cocina_id'] = int(uc_id)
                    insumos_data.append(item)
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
    receta_insumos = container.receta_service.listar_receta_insumos()
    insumos_dict = {i.id: i for i in insumos}
    ri_por_receta = {}
    for ri in receta_insumos:
        if ri.receta_id not in ri_por_receta:
            ri_por_receta[ri.receta_id] = []
        ri.insumo_obj = insumos_dict.get(ri.insumo_id)
        ri_por_receta[ri.receta_id].append(ri)
    receta.insumos = ri_por_receta.get(receta.id, [])
    unidades_cocina = container.unidad_cocina_service.listar()
    return render(request, 'inventario/crear_receta.html', {
        'editar': receta,
        'insumos': insumos,
        'unidades': Insumo.UNIDADES,
        'unidades_cocina': unidades_cocina,
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
        except Exception:
            messages.error(request, 'No se puede eliminar: esta receta esta asociada a uno o mas platos del menu.')
    return redirect('lista_recetas')


@login_required
@user_passes_test(es_admin)
def presentaciones_insumo(request, insumo_id):
    container = get_container()
    try:
        insumo = container.insumo_service.obtener_por_id(insumo_id)
    except RecursoNoEncontrado:
        messages.error(request, 'Insumo no encontrado')
        return redirect('gestion_insumos')
    presentaciones = container.presentacion_insumo_service.listar_por_insumo(insumo_id)
    if request.method == 'POST':
        try:
            container.presentacion_insumo_service.crear(
                insumo_id=insumo_id,
                nombre=request.POST.get('nombre'),
                cantidad=request.POST.get('cantidad'),
                unidad_medida=request.POST.get('unidad_medida'),
                costo_compra=request.POST.get('costo_compra', 0),
                es_principal=request.POST.get('es_principal') == 'on',
            )
            messages.success(request, 'Presentacion creada')
        except (RecursoNoEncontrado, ReglaNegocioViolada) as e:
            messages.error(request, str(e))
        return redirect('presentaciones_insumo', insumo_id=insumo_id)
    return render(request, 'inventario/presentaciones_insumo.html', {
        'insumo': insumo,
        'presentaciones': presentaciones,
        'unidades': Insumo.UNIDADES,
    })


@login_required
@user_passes_test(es_admin)
def eliminar_presentacion(request, presentacion_id):
    container = get_container()
    try:
        p = container.presentacion_insumo_service.obtener_por_id(presentacion_id)
        insumo_id = p.insumo_id
        container.presentacion_insumo_service.eliminar(presentacion_id)
        messages.success(request, 'Presentacion eliminada')
        return redirect('presentaciones_insumo', insumo_id=insumo_id)
    except RecursoNoEncontrado:
        messages.error(request, 'Presentacion no encontrada')
        return redirect('gestion_insumos')


@login_required
@user_passes_test(es_admin)
def registrar_compra_presentacion(request, presentacion_id):
    from decimal import Decimal
    container = get_container()
    try:
        p = container.presentacion_insumo_service.obtener_por_id(presentacion_id)
        if request.method == 'POST':
            container.presentacion_insumo_service.registrar_compra(
                presentacion_id=presentacion_id,
                cantidad_paquetes=int(request.POST.get('cantidad_paquetes', 1)),
                costo_total=Decimal(request.POST.get('costo_total', '0')),
                usuario=request.user,
            )
            messages.success(request, f'Compra registrada: {p.nombre}')
            return redirect('presentaciones_insumo', insumo_id=p.insumo_id)
    except RecursoNoEncontrado:
        messages.error(request, 'Presentacion no encontrada')
    return redirect('gestion_insumos')


@login_required
@user_passes_test(es_admin)
def unidades_cocina(request):
    container = get_container()
    unidades = container.unidad_cocina_service.listar()
    if request.method == 'POST':
        try:
            container.unidad_cocina_service.crear(
                nombre=request.POST.get('nombre'),
                equivalencia_cantidad=request.POST.get('equivalencia_cantidad'),
                equivalencia_unidad=request.POST.get('equivalencia_unidad'),
                grupo=request.POST.get('grupo', 'VOLUMEN'),
            )
            messages.success(request, 'Unidad de cocina creada')
        except (RecursoNoEncontrado, ReglaNegocioViolada) as e:
            messages.error(request, str(e))
        return redirect('unidades_cocina')
    return render(request, 'inventario/unidades_cocina.html', {
        'unidades': unidades,
        'unidades_medida': Insumo.UNIDADES,
    })


@login_required
@user_passes_test(es_admin)
def eliminar_unidad_cocina(request, unidad_id):
    container = get_container()
    try:
        container.unidad_cocina_service.eliminar(unidad_id)
        messages.success(request, 'Unidad de cocina eliminada')
    except RecursoNoEncontrado:
        messages.error(request, 'Unidad no encontrada')
    return redirect('unidades_cocina')

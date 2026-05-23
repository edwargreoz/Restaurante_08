
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db import IntegrityError
from django.core.exceptions import ValidationError
from core.rol_utils import es_admin, es_mozo
from .models import Insumo, Receta, RecetaInsumo

@login_required
@user_passes_test(es_mozo)
def lista_insumos(request):
    insumos= Insumo.objects.all()
    return render(request, 'inventario/lista_insumos.html', {
        'insumos': insumos,
        'es_admin': es_admin(request.user)
    })
@login_required
@user_passes_test(es_admin)
def gestion_insumos(request):
    insumos = Insumo.objects.all()
    return render(request, 'inventario/gestion_insumos.html', {'insumos': insumos})
@login_required
@user_passes_test(es_admin)
def crear_insumo(request):
    if request.method == 'POST':
        insumo = Insumo(
            nombre=request.POST.get('nombre'),
            unidad=request.POST.get('unidad'),
            stock_actual=request.POST.get('stock_actual', 0),
            stock_minimo=request.POST.get('stock_minimo', 0),
            costo_unitario=request.POST.get('costo_unitario', 0),
        )
        try:
            insumo.full_clean()
            insumo.save()
            messages.success(request, 'Insumo creado')
        except IntegrityError as e:
            if 'UNIQUE' in str(e):
                messages.error(request, 'Error: ya existe un insumo con ese nombre')
            else:
                messages.error(request, f'Error de integridad: {str(e)}')
        except ValidationError as e:
            messages.error(request, f'Error: {"; ".join(e.messages)}')
    return redirect('gestion_insumos')

@login_required
@user_passes_test(es_admin)
def editar_insumo(request, insumo_id):
    insumo = get_object_or_404(Insumo, id=insumo_id)
    if request.method == 'POST':
        insumo.nombre = request.POST.get('nombre', insumo.nombre)
        insumo.unidad = request.POST.get('unidad', insumo.unidad)
        insumo.stock_actual = request.POST.get('stock_actual', insumo.stock_actual)
        insumo.stock_minimo = request.POST.get('stock_minimo', insumo.stock_minimo)
        insumo.costo_unitario = request.POST.get('costo_unitario', insumo.costo_unitario)
        try:
            insumo.full_clean()
            insumo.save()
            messages.success(request, 'Insumo actualizado')
            return redirect('gestion_insumos')
        except (IntegrityError, ValidationError) as e:
            messages.error(request, f'Error: {str(e)}')
    return render(request, 'inventario/gestion_insumos.html', {
        'editar': insumo,
        'insumos': Insumo.objects.all(),
    })

@login_required
@user_passes_test(es_admin)
def eliminar_insumo(request, insumo_id):
    if request.method == 'POST':
        insumo = get_object_or_404(Insumo, id=insumo_id)
        insumo.delete()
        messages.success(request, 'Insumo eliminado')
    return redirect('gestion_insumos')

@login_required
@user_passes_test(es_admin)
def lista_recetas(request):
    recetas = Receta.objects.prefetch_related('insumos__insumo').all()
    return render(request, 'inventario/lista_recetas.html', {'recetas': recetas})

@login_required
@user_passes_test(es_admin)
def crear_receta(request):
    if request.method == 'POST':
        nombre_receta = request.POST.get('nombre_receta')
        if not nombre_receta:
            messages.error(request, 'El nombre de la receta es obligatorio')
            return redirect('crear_receta')
        receta, created = Receta.objects.get_or_create(nombre=nombre_receta)
        insumos_ids = request.POST.getlist('insumos[]')
        cantidades = request.POST.getlist('cantidades[]')
        unidades = request.POST.getlist('unidades[]')
        if not insumos_ids:
            messages.error(request, 'Debe agregar al menos un insumo')
            return redirect('crear_receta')
        errores = []
        exitos = 0
        for insumo_id, cantidad, unidad in zip(insumos_ids, cantidades, unidades):
            if not insumo_id or not cantidad:
                continue
            try:
                ri = RecetaInsumo(
                    receta=receta,
                    insumo_id=insumo_id,
                    cantidad_por_porcion=cantidad,
                    unidad=unidad,
                )
                ri.full_clean()
                ri.save()
                exitos += 1
            except IntegrityError:
                insumo = Insumo.objects.get(id=insumo_id)
                errores.append(f"'{insumo.nombre}' ya está en la receta")
            except ValidationError as e:
                errores.append(str(e))
        if created:
            messages.success(request, f'Receta "{nombre_receta}" creada')
        if exitos:
            messages.success(request, f'{exitos} insumo(s) agregado(s)')
        for err in errores:
            messages.error(request, err)
        return redirect('lista_recetas')
    insumos = Insumo.objects.all()
    return render(request, 'inventario/crear_receta.html', {
        'insumos': insumos,
        'unidades': Insumo.UNIDADES,
    })

@login_required
@user_passes_test(es_admin)
def editar_receta(request, receta_id):
    receta = get_object_or_404(Receta, id=receta_id)
    if request.method == 'POST':
        nombre_receta = request.POST.get('nombre_receta')
        if nombre_receta:
            receta.nombre = nombre_receta
            receta.save()
        insumos_ids = request.POST.getlist('insumos[]')
        cantidades = request.POST.getlist('cantidades[]')
        unidades = request.POST.getlist('unidades[]')
        if insumos_ids:
            receta.insumos.all().delete()
            errores = []
            exitos = 0
            for insumo_id, cantidad, unidad in zip(insumos_ids, cantidades, unidades):
                if not insumo_id or not cantidad:
                    continue
                try:
                    ri = RecetaInsumo(
                        receta=receta,
                        insumo_id=insumo_id,
                        cantidad_por_porcion=cantidad,
                        unidad=unidad,
                    )
                    ri.full_clean()
                    ri.save()
                    exitos += 1
                except ValidationError as e:
                    errores.append(str(e))
            if exitos:
                messages.success(request, f'Receta "{receta.nombre}" actualizada ({exitos} insumo(s))')
            for err in errores:
                messages.error(request, err)
        return redirect('lista_recetas')
    insumos = Insumo.objects.all()
    return render(request, 'inventario/crear_receta.html', {
        'editar': receta,
        'insumos': insumos,
        'unidades': Insumo.UNIDADES,
    })

@login_required
@user_passes_test(es_admin)
def eliminar_receta(request, receta_insumo_id):
    receta_insumo = get_object_or_404(RecetaInsumo, id=receta_insumo_id)
    if request.method == 'POST':
        receta_insumo.delete()
        messages.success(request, 'Insumo eliminado de la receta')
    return redirect('lista_recetas')


@login_required
@user_passes_test(es_admin)
def eliminar_receta_completa(request, receta_id):
    receta = get_object_or_404(Receta, id=receta_id)
    if request.method == 'POST':
        receta.delete()
        messages.success(request, f'Receta "{receta.nombre}" eliminada')
    return redirect('lista_recetas')


from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db import IntegrityError
from django.core.exceptions import ValidationError
from menu.models import Plato
from core.rol_utils import es_admin, es_mozo
from .models import Insumo, RecetaInsumo

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
    recetas = RecetaInsumo.objects.select_related('plato', 'insumo').all()
    return render(request, 'inventario/lista_recetas.html', {'recetas': recetas})

@login_required
@user_passes_test(es_admin)
def crear_receta(request):
    if request.method == 'POST':
        receta = RecetaInsumo(
            plato_id=request.POST.get('plato_id'),
            insumo_id=request.POST.get('insumo_id'),
            cantidad_por_porcion=request.POST.get('cantidad_por_porcion'),
        )
        try:
            receta.full_clean()
            receta.save()
            messages.success(request, 'Receta creada')
        except (IntegrityError, ValidationError) as e:
            messages.error(request, f'Error: {str(e)}')
        return redirect('lista_recetas')
    platos = Plato.objects.all()
    insumos = Insumo.objects.all()
    return render(request, 'inventario/crear_receta.html', {
        'platos': platos, 'insumos': insumos
    })

@login_required
@user_passes_test(es_admin)
def eliminar_receta(request, receta_id):
    receta = get_object_or_404(RecetaInsumo, id=receta_id)
    if request.method == 'POST':
        receta.delete()
        messages.success(request, 'Receta eliminada')
    return redirect('lista_recetas')

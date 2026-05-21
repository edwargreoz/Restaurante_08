

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Insumo

@login_required
def lista_insumos(request):
    insumos= Insumo.objects.all()
    return render(request, 'inventario/lista_insumos.html',
                  {'insumos':insumos})
@login_required
def gestion_insumos(request):
    insumos = Insumo.objects.all()
    return render(request, 'inventario/gestion_insumos.html', {'insumos': insumos})
@login_required
def crear_insumo(request):
    if request.method == 'POST':
        Insumo.objects.create(
            nombre=request.POST.get('nombre'),
            unidad=request.POST.get('unidad'),
            stock_actual=request.POST.get('stock_actual', 0),
            stock_minimo=request.POST.get('stock_minimo', 0),
            costo_unitario=request.POST.get('costo_unitario', 0),
        )
        messages.success(request, 'Insumo creado')
    return redirect('gestion_insumos')

@login_required
def editar_insumo(request, insumo_id):
    insumo = get_object_or_404(Insumo, id=insumo_id)
    if request.method == 'POST':
        insumo.nombre = request.POST.get('nombre', insumo.nombre)
        insumo.unidad = request.POST.get('unidad', insumo.unidad)
        insumo.stock_actual = request.POST.get('stock_actual', insumo.stock_actual)
        insumo.stock_minimo = request.POST.get('stock_minimo', insumo.stock_minimo)
        insumo.costo_unitario = request.POST.get('costo_unitario', insumo.costo_unitario)
        insumo.save()
        messages.success(request, 'Insumo actualizado')
        return redirect('gestion_insumos')
    return render(request, 'inventario/gestion_insumos.html', {
        'editar': insumo,
        'insumos': Insumo.objects.all(),
    })

@login_required
def eliminar_insumo(request, insumo_id):
    if request.method == 'POST':
        insumo = get_object_or_404(Insumo, id=insumo_id)
        insumo.delete()
        messages.success(request, 'Insumo eliminado')
    return redirect('gestion_insumos')

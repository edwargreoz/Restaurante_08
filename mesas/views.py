

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import ValidationError
from .models import Mesa,UnionMesa
from pedidos.models import Comanda
from menu.models import Categoria


@login_required
def plano_mesas(request): 
    mesas = Mesa.objects.all()
    return render(request, 'mesas/plano_mesas.html', {'mesas':mesas})

@login_required
def detalle_mesa(request, mesa_id):
    mesa = get_object_or_404(Mesa, id=mesa_id)
    comanda_activa = Comanda.objects.filter(
        mesa=mesa, estado__in=['ABIERTA', 'EN_PREPARACION', 'LISTA']
    ).prefetch_related('lineas__plato').first()
    categorias = Categoria.objects.prefetch_related('platos').all()
    return render(request, 'mesas/detalle_mesa.html', {
        'mesa': mesa,
        'comanda_activa': comanda_activa,
        'categorias': categorias,
    })

@login_required
def abrir_comanda(request, mesa_id):
    if request.method == 'POST':
        try:
            Comanda.abrir(mesa_id, request.user)
            messages.success(request, 'Comanda abierta')
        except ValidationError as e:
            messages.error(request, str(e))
    return redirect('detalle_mesa', mesa_id=mesa_id)

@login_required
def agregar_plato_comanda(request, comanda_id):
    if request.method=='POST':
        comanda = get_object_or_404(Comanda, id=comanda_id)
        try:
            comanda.agregar_platos([{
                'plato_id': int(request.POST.get('plato_id')),
                'cantidad':int(request.POST.get('cantidad', 1)),
                'observacion': request.POST.get('observacion', ''),

            }])
            messages.success(request, 'Plato agregado')
        except ValidationError as e:
            for error in e.message_dict.get('errores', [str(e)]):
                if isinstance(error, dict):
                    messages.error(request, error.get('error', str(error)))
                else:
                    messages.error(request, error)
    return redirect('detalle_mesa', mesa_id=comanda.mesa.id)
@login_required
def unir_mesas(request):
    mesas = Mesa.objects.all()
    uniones = UnionMesa.objects.filter(activa=True).prefetch_related('mesas')
    if request.method == 'POST':
        mesa_ids = request.POST.getlist('mesas')
        if len(mesa_ids) >= 2:
            mesas_validas = Mesa.objects.filter(id__in=mesa_ids)
            if mesas_validas.count() < 2:
                messages.error(request, 'Las mesas seleccionadas no existen')
                return redirect('unir_mesas')
            
            union = UnionMesa.objects.create()
            union.mesas.set(mesas_validas)
            union.save()
            comandas_activas = Comanda.objects.filter(
                mesa_id__in=mesa_ids,
                estado__in=['ABIERTA', 'EN_PREPARACION', 'LISTA']
            )
            if comandas_activas.count() >= 2:
                principal = comandas_activas.first()
                for otras in comandas_activas[1:]:
                    principal.fusionar(otras)
            messages.success(request, 'Unión creada')
        else:
            messages.error(request, 'Selecciona al menos 2 mesas')
        return redirect('unir_mesas')
    return render(request, 'mesas/unir_mesas.html', {
        'mesas': mesas,
        'uniones': uniones,
    })
@login_required
def deshacer_union(request, union_id):
    if request.method == 'POST':
        union = get_object_or_404(UnionMesa, id=union_id, activa=True)
        for mesa in union.mesas.all():
            mesa.estado = 'LIBRE'
            mesa.save()
        union.activa = False
        union.save()
        messages.success(request, 'Unión deshecha, mesas liberadas')
    return redirect('unir_mesas')

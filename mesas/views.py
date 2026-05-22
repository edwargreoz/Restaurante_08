

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.utils import timezone
from core.rol_utils import es_mozo
from .models import Mesa,UnionMesa
from pedidos.models import Comanda
from menu.models import Categoria


@login_required
@user_passes_test(es_mozo)
def plano_mesas(request): 
    mesas = Mesa.objects.all()
    uniones = UnionMesa.objects.filter(activa=True).prefetch_related('mesas')
    union_mesas_ids = set()
    union_labels = {}
    for union in uniones:
        miembros = list(union.mesas.all())
        nums = sorted([m.numero for m in miembros])
        label = ' + '.join([f'Mesa {x}' for x in nums])
        for m in miembros:
            union_mesas_ids.add(m.id)
            union_labels[m.id] = label
    return render(request, 'mesas/plano_mesas.html', {
        'mesas': mesas,
        'union_mesas_ids': union_mesas_ids,
        'union_labels': union_labels,
    })

@login_required
@user_passes_test(es_mozo)
def detalle_mesa(request, mesa_id):
    mesa = get_object_or_404(Mesa, id=mesa_id)
    comanda_activa = Comanda.objects.filter(
        mesa=mesa, estado__in=['ABIERTA', 'EN_PREPARACION', 'LISTA']
    ).prefetch_related('lineas__plato').first()
    if comanda_activa and mesa.estado == 'LIBRE':
        try:
            comanda_activa.anular(usuario=request.user)
        except ValidationError:
            comanda_activa.estado = 'ANULADA'
            comanda_activa.fecha_cierre = timezone.now()
            comanda_activa.save()
        comanda_activa = None
        messages.info(request, 'Se anuló una comanda huérfana de la mesa')
    union_activa = UnionMesa.objects.filter(mesas=mesa, activa=True).prefetch_related('mesas').first()
    if not comanda_activa and union_activa:
        comanda_activa = Comanda.objects.filter(
            mesa__in=union_activa.mesas.all(),
            estado__in=['ABIERTA', 'EN_PREPARACION', 'LISTA']
        ).prefetch_related('lineas__plato').first()
    categorias = Categoria.objects.prefetch_related('platos').all()
    return render(request, 'mesas/detalle_mesa.html', {
        'mesa': mesa,
        'comanda_activa': comanda_activa,
        'categorias': categorias,
        'union_activa': union_activa,
    })

@login_required
@user_passes_test(es_mozo)
def abrir_comanda(request, mesa_id):
    if request.method == 'POST':
        try:
            Comanda.abrir(mesa_id, request.user)
            messages.success(request, 'Comanda abierta')
        except ValidationError as e:
            messages.error(request, str(e))
    return redirect('detalle_mesa', mesa_id=mesa_id)

@login_required
@user_passes_test(es_mozo)
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
@user_passes_test(es_mozo)
def anular_comanda(request, comanda_id):
    comanda = get_object_or_404(Comanda, id=comanda_id)
    if request.method == 'POST':
        try:
            comanda.anular(usuario=request.user)
            messages.success(request, 'Comanda anulada, mesa liberada')
        except ValidationError as e:
            messages.error(request, str(e))
    return redirect('detalle_mesa', mesa_id=comanda.mesa.id)

@login_required
@user_passes_test(es_mozo)
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
            
            selected_ids = set(int(id) for id in mesa_ids)
            for union_existente in uniones:
                union_ids = set(m.id for m in union_existente.mesas.all())
                if union_ids == selected_ids:
                    messages.error(request, 'Ya existe una unión activa con esas mesas')
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
            primera = mesas_validas.first()
            return redirect('detalle_mesa', mesa_id=primera.id)
        else:
            messages.error(request, 'Selecciona al menos 2 mesas')
        return redirect('unir_mesas')
    union_mesas_ids = set()
    for u in uniones:
        for m in u.mesas.all():
            union_mesas_ids.add(m.id)
    mesas_disponibles = mesas.exclude(id__in=union_mesas_ids)
    return render(request, 'mesas/unir_mesas.html', {
        'mesas': mesas,
        'uniones': uniones,
        'union_mesas_ids': union_mesas_ids,
        'mesas_disponibles': mesas_disponibles,
    })
@login_required
@user_passes_test(es_mozo)
def agregar_mesa_union(request, union_id):
    if request.method == 'POST':
        union = get_object_or_404(UnionMesa, id=union_id, activa=True)
        mesa_id = request.POST.get('mesa_id')
        if mesa_id:
            mesa = get_object_or_404(Mesa, id=mesa_id)
            if union.mesas.filter(id=mesa_id).exists():
                messages.error(request, f'Mesa {mesa.numero} ya está en la unión')
            else:
                union.mesas.add(mesa)
                comanda_union = Comanda.objects.filter(
                    mesa__in=union.mesas.all(),
                    estado__in=['ABIERTA', 'EN_PREPARACION', 'LISTA']
                ).exclude(mesa=mesa).first()
                if comanda_union:
                    from caja.models import Caja
                    if not Caja.objects.filter(estado='ABIERTA').exists():
                        messages.error(request, 'No hay un turno de caja abierto')
                        return redirect('unir_mesas')
                    mesa.estado = 'OCUPADA'
                    mesa.save()
                    comanda_nueva = Comanda.objects.create(mesa=mesa, mozo=request.user)
                    comanda_union.fusionar(comanda_nueva)
                else:
                    Comanda.abrir(mesa.id, request.user)
                messages.success(request, f'Mesa {mesa.numero} agregada a la unión')
        return redirect('unir_mesas')
    return redirect('unir_mesas')

@login_required
@user_passes_test(es_mozo)
def deshacer_union(request, union_id):
    if request.method == 'POST':
        union = get_object_or_404(UnionMesa, id=union_id, activa=True)
        mesa_ids = [m.id for m in union.mesas.all()]
        comandas_activas = Comanda.objects.filter(
            mesa_id__in=mesa_ids,
            estado__in=['ABIERTA', 'EN_PREPARACION', 'LISTA']
        )
        for comanda in comandas_activas:
            try:
                comanda.anular(usuario=request.user)
            except ValidationError:
                comanda.estado = 'ANULADA'
                comanda.fecha_cierre = timezone.now()
                comanda.save()
        union.activa = False
        union.save()
        messages.success(request, 'Unión deshecha, comandas anuladas, mesas liberadas')
    return redirect('unir_mesas')

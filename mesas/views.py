from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from core.rol_utils import es_mozo, es_admin
from core.excepciones import (
    RecursoNoEncontrado, UnionInvalida, ReglaNegocioViolada, CajaNoAbierta,
)
from .models import Mesa, UnionMesa
from .forms import MesaForm
from .services import MesaService, UnionMesaService
from pedidos.models import Comanda
from pedidos.views import _procesar_agregar_plato
from menu.models import Categoria


@login_required
@user_passes_test(es_mozo)
def plano_mesas(request):
    mesas = Mesa.activos.all()
    uniones = UnionMesa.activos.prefetch_related('mesas')
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
    mesa = get_object_or_404(Mesa.activos, id=mesa_id)
    comanda_activa = Comanda.objects.filter(
        mesa=mesa, estado__in=['ABIERTA', 'EN_PREPARACION', 'LISTA']
    ).prefetch_related('lineas__plato').first()
    if comanda_activa and mesa.estado == 'LIBRE':
        try:
            comanda_activa.anular(usuario=request.user)
            messages.info(request, 'Se anuló una comanda huérfana de la mesa')
        except ReglaNegocioViolada:
            messages.error(request, 'No se pudo anular la comanda huérfana')
        comanda_activa = None
    union_activa = UnionMesa.activos.filter(mesas=mesa).prefetch_related('mesas').first()
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
            MesaService.obtener_o_crear_comanda_activa(mesa_id, request.user)
            messages.success(request, 'Comanda abierta')
        except ReglaNegocioViolada as e:
            messages.error(request, str(e))
    return redirect('detalle_mesa', mesa_id=mesa_id)


@login_required
@user_passes_test(es_mozo)
def agregar_plato_comanda(request, comanda_id):
    comanda = get_object_or_404(Comanda, id=comanda_id)
    if request.method == 'POST':
        _procesar_agregar_plato(request, comanda)
    return redirect('detalle_mesa', mesa_id=comanda.mesa.id)


@login_required
@user_passes_test(es_mozo)
def anular_comanda(request, comanda_id):
    comanda = get_object_or_404(Comanda, id=comanda_id)
    if request.method == 'POST':
        try:
            from pedidos.services import ComandaService
            ComandaService.anular(comanda.id, request.user)
            messages.success(request, 'Comanda anulada, mesa liberada')
        except ReglaNegocioViolada as e:
            messages.error(request, str(e))
    return redirect('detalle_mesa', mesa_id=comanda.mesa.id)


@login_required
@user_passes_test(es_mozo)
def marcar_mesa_libre(request, mesa_id):
    if request.method == 'POST':
        try:
            MesaService.marcar_libre(mesa_id)
            messages.success(request, 'Mesa marcada como libre')
        except (RecursoNoEncontrado, ReglaNegocioViolada) as e:
            messages.error(request, str(e))
    return redirect('plano_mesas')


@login_required
@user_passes_test(es_mozo)
def unir_mesas(request):
    mesas = Mesa.activos.all()
    uniones = UnionMesa.activos.prefetch_related('mesas')
    if request.method == 'POST':
        mesa_ids = request.POST.getlist('mesas')
        try:
            mesa_ids_int = [int(x) for x in mesa_ids]
            union = UnionMesaService.crear(mesa_ids_int)
            messages.success(request, 'Unión creada')
            primera = union.mesas.first()
            return redirect('detalle_mesa', mesa_id=primera.id)
        except UnionInvalida as e:
            messages.error(request, str(e))
            return redirect('unir_mesas')
        except (ValueError, TypeError):
            messages.error(request, 'Selecciona al menos 2 mesas')
            return redirect('unir_mesas')
    union_mesas_ids = set()
    for u in uniones:
        for m in u.mesas.all():
            union_mesas_ids.add(m.id)
    mesas_disponibles = mesas.exclude(id__in=union_mesas_ids).exclude(estado='RESERVADA')
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
        mesa_id = request.POST.get('mesa_id')
        if mesa_id:
            try:
                UnionMesaService.agregar_mesa(union_id, int(mesa_id), request.user)
                messages.success(request, 'Mesa agregada a la unión')
            except (RecursoNoEncontrado, UnionInvalida, CajaNoAbierta) as e:
                messages.error(request, str(e))
        return redirect('unir_mesas')
    return redirect('unir_mesas')


@login_required
@user_passes_test(es_mozo)
def deshacer_union(request, union_id):
    if request.method == 'POST':
        try:
            UnionMesaService.deshacer(union_id, request.user)
            messages.success(request, 'Unión deshecha, comandas anuladas, mesas liberadas')
        except (RecursoNoEncontrado, UnionInvalida) as e:
            messages.error(request, str(e))
    return redirect('unir_mesas')


# ----------------- VISTAS DE ADMINISTRADOR (CRUD MESAS) -----------------

@login_required
@user_passes_test(es_admin)
def lista_mesas_admin(request):
    if request.method == 'POST':
        form = MesaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Mesa creada exitosamente.')
            return redirect('lista_mesas_admin')
    else:
        form = MesaForm()

    mesas = Mesa.activos.order_by('numero')
    return render(request, 'mesas/lista_mesas_admin.html', {'mesas': mesas, 'form': form})


@login_required
@user_passes_test(es_admin)
def crear_mesa(request):
    if request.method == 'POST':
        form = MesaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Mesa creada exitosamente.')
            return redirect('lista_mesas_admin')
    else:
        form = MesaForm()

    return render(request, 'mesas/form_mesa.html', {'form': form, 'titulo': 'Crear Nueva Mesa'})


@login_required
@user_passes_test(es_admin)
def editar_mesa(request, mesa_id):
    mesa = get_object_or_404(Mesa.activos, id=mesa_id)
    if mesa.estado == 'RESERVADA':
        messages.error(request, 'No puedes editar una mesa que actualmente se encuentra RESERVADA.')
        return redirect('lista_mesas_admin')

    if request.method == 'POST':
        form = MesaForm(request.POST, instance=mesa)
        if form.is_valid():
            form.save()
            messages.success(request, f'Mesa {mesa.numero} actualizada exitosamente.')
            return redirect('lista_mesas_admin')
    else:
        form = MesaForm(instance=mesa)

    return render(request, 'mesas/form_mesa.html', {'form': form, 'titulo': f'Editar Mesa {mesa.numero}'})


@login_required
@user_passes_test(es_admin)
def eliminar_mesa(request, mesa_id):
    mesa = get_object_or_404(Mesa.activos, id=mesa_id)
    if request.method == 'POST':
        if mesa.estado != 'LIBRE':
            messages.error(request, 'No puedes eliminar una mesa que no está LIBRE.')
            return redirect('lista_mesas_admin')
        mesa.eliminar(usuario=request.user)
        messages.success(request, f'Mesa {mesa.numero} eliminada lógicamente.')
        return redirect('lista_mesas_admin')

    return render(request, 'mesas/eliminar_mesa_confirmar.html', {'mesa': mesa})

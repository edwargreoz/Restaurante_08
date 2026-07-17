from django.shortcuts import render, redirect
from django.http import Http404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from core.rol_utils import es_mozo, es_admin
from core.excepciones import (
    RecursoNoEncontrado, UnionInvalida, ReglaNegocioViolada, CajaNoAbierta, AppError,
    StockInsuficiente,
)
from infraestructura.container import get_container
from .models import Mesa, UnionMesa
from .forms import MesaForm
from pedidos.models import Comanda


@login_required
@user_passes_test(es_mozo)
def plano_mesas(request):
    container = get_container()
    data = container.mesa_service.obtener_plano()
    return render(request, 'mesas/plano_mesas.html', data)


@login_required
@user_passes_test(es_mozo)
def detalle_mesa(request, mesa_id):
    container = get_container()
    data = container.mesa_service.obtener_detalle(mesa_id, usuario=request.user)
    return render(request, 'mesas/detalle_mesa.html', data)


@login_required
@user_passes_test(es_mozo)
def abrir_comanda(request, mesa_id):
    if request.method == 'POST':
        try:
            container = get_container()
            container.mesa_service.obtener_o_crear_comanda_activa(mesa_id, request.user)
            messages.success(request, 'Comanda abierta')
        except AppError as e:
            messages.error(request, str(e))
    return redirect('detalle_mesa', mesa_id=mesa_id)


@login_required
@user_passes_test(es_mozo)
def agregar_plato_comanda(request, comanda_id):
    container = get_container()
    comanda = container.comanda_service.comanda_repo.obtener_por_id(comanda_id)
    if not comanda:
        raise Http404()
    if request.method == 'POST':
        try:
            container = get_container()
            container.comanda_service.agregar_platos(comanda.id, [{
                'plato_id': int(request.POST.get('plato_id')),
                'cantidad': int(request.POST.get('cantidad', 1)),
                'observacion': request.POST.get('observacion', ''),
            }], usuario=request.user)
            messages.success(request, 'Plato agregado')
        except StockInsuficiente as e:
            errores = e.args[0].get('errores', []) if e.args else []
            for error in errores:
                messages.error(request, error.get('error', str(error)))
        except AppError as e:
            messages.error(request, str(e))
    return redirect('detalle_mesa', mesa_id=comanda.mesa_id)


@login_required
@user_passes_test(es_mozo)
def anular_comanda(request, comanda_id):
    container = get_container()
    comanda = container.comanda_service.comanda_repo.obtener_por_id(comanda_id)
    if not comanda:
        raise Http404()
    if request.method == 'POST':
        try:
            container = get_container()
            container.comanda_service.anular(comanda.id, usuario=request.user)
            messages.success(request, 'Comanda anulada, mesa liberada')
        except AppError as e:
            messages.error(request, str(e))
    return redirect('detalle_mesa', mesa_id=comanda.mesa_id)


@login_required
@user_passes_test(es_mozo)
def marcar_mesa_libre(request, mesa_id):
    if request.method == 'POST':
        try:
            container = get_container()
            container.mesa_service.marcar_libre(mesa_id)
            messages.success(request, 'Mesa marcada como libre')
        except (RecursoNoEncontrado, ReglaNegocioViolada) as e:
            messages.error(request, str(e))
    return redirect('plano_mesas')


@login_required
@user_passes_test(es_mozo)
def unir_mesas(request):
    container = get_container()
    datos = container.union_mesa_service.obtener_datos_para_union()
    if request.method == 'POST':
        mesa_ids = request.POST.getlist('mesas')
        try:
            mesa_ids_int = [int(x) for x in mesa_ids]
            union = container.union_mesa_service.crear(mesa_ids_int)
            messages.success(request, 'Unión creada')
            primera = union.mesas.first()
            return redirect('detalle_mesa', mesa_id=primera.id)
        except UnionInvalida as e:
            messages.error(request, str(e))
            return redirect('unir_mesas')
        except (ValueError, TypeError):
            messages.error(request, 'Selecciona al menos 2 mesas')
            return redirect('unir_mesas')
    return render(request, 'mesas/unir_mesas.html', datos)


@login_required
@user_passes_test(es_mozo)
def agregar_mesa_union(request, union_id):
    if request.method == 'POST':
        mesa_id = request.POST.get('mesa_id')
        if mesa_id:
            try:
                container = get_container()
                container.union_mesa_service.agregar_mesa(union_id, int(mesa_id), request.user)
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
            container = get_container()
            container.union_mesa_service.deshacer(union_id, request.user)
            messages.success(request, 'Unión deshecha, comandas anuladas, mesas liberadas')
        except (RecursoNoEncontrado, UnionInvalida) as e:
            messages.error(request, str(e))
    return redirect('plano_mesas')


# ----------------- VISTAS DE ADMINISTRADOR (CRUD MESAS) -----------------

@login_required
@user_passes_test(es_admin)
def lista_mesas_admin(request):
    if request.method == 'POST':
        form = MesaForm(request.POST)
        if form.is_valid():
            container = get_container()
            container.mesa_service.crear(
                numero=form.cleaned_data['numero'],
                capacidad=form.cleaned_data['capacidad'],
                zona=form.cleaned_data['zona'],
                estado=form.cleaned_data['estado'],
            )
            messages.success(request, 'Mesa creada exitosamente.')
            return redirect('lista_mesas_admin')
    else:
        form = MesaForm()

    container = get_container()
    mesas = container.mesa_service.mesa_repo.listar_activas() # Asumiendo que el repo tiene este método
    # Nota: Si el repo no soporta order_by en DB, se asume que las retorna ordenadas o se ordenan en memoria.
    mesas = sorted(mesas, key=lambda m: m.numero)
    return render(request, 'mesas/lista_mesas_admin.html', {'mesas': mesas, 'form': form})


@login_required
@user_passes_test(es_admin)
def crear_mesa(request):
    if request.method == 'POST':
        form = MesaForm(request.POST)
        if form.is_valid():
            container = get_container()
            container.mesa_service.crear(
                numero=form.cleaned_data['numero'],
                capacidad=form.cleaned_data['capacidad'],
                zona=form.cleaned_data['zona'],
                estado=form.cleaned_data['estado'],
            )
            messages.success(request, 'Mesa creada exitosamente.')
            return redirect('lista_mesas_admin')
    else:
        form = MesaForm()

    return render(request, 'mesas/form_mesa.html', {'form': form, 'titulo': 'Crear Nueva Mesa'})


@login_required
@user_passes_test(es_admin)
def editar_mesa(request, mesa_id):
    container = get_container()
    try:
        container.mesa_service.validar_editable(mesa_id)
    except ReglaNegocioViolada as e:
        messages.error(request, str(e))
        return redirect('lista_mesas_admin')

    mesa_model = container.mesa_service.obtener_modelo(mesa_id)

    if request.method == 'POST':
        form = MesaForm(request.POST, instance=mesa_model)
        if form.is_valid():
            container.mesa_service.editar(
                mesa_id=mesa_model.id,
                numero=form.cleaned_data['numero'],
                capacidad=form.cleaned_data['capacidad'],
                zona=form.cleaned_data['zona'],
                estado=form.cleaned_data['estado'],
            )
            messages.success(request, f'Mesa {mesa_model.numero} actualizada exitosamente.')
            return redirect('lista_mesas_admin')
    else:
        form = MesaForm(instance=mesa_model)

    return render(request, 'mesas/form_mesa.html', {'form': form, 'titulo': f'Editar Mesa {mesa_model.numero}'})


@login_required
@user_passes_test(es_admin)
def eliminar_mesa(request, mesa_id):
    container = get_container()
    mesa = container.mesa_service.mesa_repo.obtener_por_id(mesa_id)
    if not mesa:
        raise Http404()
    if request.method == 'POST':
        try:
            container = get_container()
            container.mesa_service.eliminar(mesa.id, usuario=request.user)
            messages.success(request, f'Mesa {mesa.numero} eliminada lógicamente.')
        except AppError as e:
            messages.error(request, str(e))
        return redirect('lista_mesas_admin')

    return render(request, 'mesas/eliminar_mesa_confirmar.html', {'mesa': mesa})

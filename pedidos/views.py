
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from core.rol_utils import es_mozo, es_cocinero, es_mozo_o_cocinero
from core.excepciones import AppError, StockInsuficiente
from infraestructura.container import get_container

from django.http import Http404


@login_required
@user_passes_test(es_mozo)
def tomar_pedido(request, mesa_id):
    container = get_container()
    try:
        data = container.comanda_service.obtener_datos_tomar_pedido(mesa_id)
    except AppError:
        raise Http404()
    return render(request, 'pedidos/tomar_pedido.html', data)


def _procesar_agregar_plato(request, comanda):
    try:
        container = get_container()
        container.comanda_service.agregar_platos(comanda.id, [{
            'plato_id': int(request.POST.get('plato_id')),
            'cantidad': int(request.POST.get('cantidad', 1)),
            'observacion': request.POST.get('observacion', ''),
        }], usuario=request.user)
        messages.success(request, 'Plato agregado')
        return True
    except StockInsuficiente as e:
        errores = e.args[0].get('errores', []) if e.args else []
        for error in errores:
            messages.error(request, error.get('error', str(error)))
        return False
    except AppError as e:
        messages.error(request, str(e))
        return False


@login_required
@user_passes_test(es_mozo)
def agregar_platos_pedido(request, comanda_id):
    container = get_container()
    comanda = container.comanda_service.obtener_por_id(comanda_id)
    if not comanda:
        raise Http404()
    if request.method == 'POST':
        _procesar_agregar_plato(request, comanda)
    return redirect('tomar_pedido', mesa_id=comanda.mesa_id)


# kds cocina

@login_required
@user_passes_test(es_cocinero)
def kds_panel(request):
    container = get_container()
    comandas = container.linea_comanda_service.obtener_panel_kds()
    return render(request, 'cocina/kds_panel.html', {'comandas': comandas})


@login_required
@user_passes_test(es_mozo_o_cocinero)
def enviar_cocina(request, linea_id):
    if request.method == 'POST':
        try:
            container = get_container()
            container.linea_comanda_service.enviar_cocina(linea_id)
            messages.success(request, 'Linea enviada a cocina')
        except AppError as e:
            messages.error(request, str(e))
    return redirect('kds_panel')


@login_required
@user_passes_test(es_cocinero)
def marcar_listo(request, linea_id):
    if request.method == 'POST':
        try:
            container = get_container()
            container.linea_comanda_service.marcar_listo(linea_id)
            messages.success(request, 'Linea marcada como lista')
        except AppError as e:
            messages.error(request, str(e))
    return redirect('kds_panel')

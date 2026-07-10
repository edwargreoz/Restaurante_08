
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Q
from core.rol_utils import es_mozo, es_cocinero, es_mozo_o_cocinero
from pedidos.models import Comanda, LineaComanda
from pedidos.services import ComandaService, LineaComandaService
from core.excepciones import AppError, StockInsuficiente
from mesas.models import Mesa
from menu.models import Categoria

@login_required
@user_passes_test(es_mozo)
def tomar_pedido(request, mesa_id):
    mesa = get_object_or_404(Mesa, id=mesa_id)
    comanda = Comanda.objects.filter(
        mesa =mesa, estado__in=['ABIERTA','EN_PREPARACION','LISTA']
    ).prefetch_related('lineas__plato').first()
    categorias = Categoria.objects.prefetch_related('platos').all()
    return render(request, 'pedidos/tomar_pedido.html',{
        'mesa':mesa,
        'comanda':comanda,
        'categorias':categorias
    })
def _procesar_agregar_plato(request, comanda):
    try:
        ComandaService.agregar_platos(comanda.id, [{
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
    comanda = get_object_or_404(Comanda, id=comanda_id)
    if request.method == 'POST':
        _procesar_agregar_plato(request, comanda)
    return redirect('tomar_pedido', mesa_id=comanda.mesa.id)

#kds cocina

@login_required
@user_passes_test(es_cocinero)
def kds_panel(request):
    comanda_ids = LineaComanda.objects.filter(
        estado__in=['PENDIENTE', 'EN_PREP']
    ).values_list('comanda_id', flat=True).distinct()

    comandas = Comanda.objects.filter(
        Q(estado='EN_PREPARACION') | Q(id__in=comanda_ids)
    ).prefetch_related(
        'lineas__plato', 'mozo', 'mesa'
    ).order_by('fecha_apertura')

    return render(request, 'cocina/kds_panel.html', {'comandas': comandas})
@login_required
@user_passes_test(es_mozo_o_cocinero)
def enviar_cocina(request, linea_id):
    if request.method == 'POST':
        try:
            LineaComandaService.enviar_cocina(linea_id)
            messages.success(request, 'Línea enviada a cocina')
        except AppError as e:
            messages.error(request, str(e))
    return redirect('kds_panel')

@login_required
@user_passes_test(es_cocinero)
def marcar_listo(request, linea_id):
    if request.method == 'POST':
        try:
            LineaComandaService.marcar_listo(linea_id)
            messages.success(request, 'Linea marcada como lista')
        except AppError as e:
            messages.error(request, str(e))
    return redirect('kds_panel')
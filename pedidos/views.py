
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Q
from pedidos.models import Comanda, LineaComanda
from mesas.models import Mesa
from menu.models import Categoria

@login_required
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
@login_required
def agregar_platos_pedido(request, comanda_id):
    if request.method == 'POST':
        comanda = get_object_or_404(Comanda, id=comanda_id)
        plato_id = request.POST.get('plato_id')
        cantidad = request.POST.get('cantidad',1)
        observacion = request.POST.get('observacion','')
        try:
            comanda.agregar_platos([{
                'plato_id':int(plato_id),
                'cantidad':int(cantidad),
                'observacion': observacion
            }])
            messages.success(request, 'Plato agregado')
        except ValidationError as e:
            for error in e.message_dict.get('errores', [str(e)]):
                if isinstance(error, dict):
                    messages.error(request, error.get('error', str(error)))
                else:
                    messages.error(request, error)
    return redirect('tomar_pedido', mesa_id=comanda.mesa.id)

#kds cocina

@login_required
def kds_panel(request):
    comandas= Comanda.objects.filter(
        Q(estado='EN_PREPARACION') | Q(lineas__estado__in=['PENDIENTE','EN_PREP'])
    ).distinct().prefetch_related('lineas__plato','mozo','mesa').order_by(
        'fecha_apertura'
    )
    return render(request, 'cocina/kds_panel.html',{'comandas':comandas})
@login_required
def enviar_cocina(request, linea_id):
    if request.method == 'POST':
        linea = get_object_or_404(LineaComanda, id=linea_id)
        try:
            linea.enviar_cocina()
            messages.success(request, 'Línea enviada a cocina')
        except ValidationError as e:
            messages.error(request, str(e))
    return redirect('kds_panel')

@login_required
def marcar_listo(request, linea_id):
    if request.method == 'POST':
        linea = get_object_or_404(LineaComanda, id = linea_id)
        try:
            linea.marcar_listo()
            messages.success(request, 'Linea marcada como lista')
        except ValidationError as e:
            messages.error(request, str(e))
    return redirect('kds_panel')
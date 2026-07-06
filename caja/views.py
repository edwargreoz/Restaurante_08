
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.exceptions import ValidationError
from core.excepciones import CajaNoAbierta, RecursoNoEncontrado, ReglaNegocioViolada
from pedidos.models import Comanda
from caja.models import Caja, Pago
from core.rol_utils import es_mozo_o_cajero, es_cajero_o_admin
from .services import CajaService, PagoService

@login_required
@user_passes_test(es_mozo_o_cajero)
def cobrar_comanda(request, comanda_id):
    comanda = get_object_or_404(
        Comanda.objects.prefetch_related('lineas__plato', 'pagos'),
        id=comanda_id, estado='LISTA'
    )
    if request.method == 'POST':
        try:
            caja_activa = CajaService.obtener_activa()
        except CajaNoAbierta as e:
            messages.error(request, str(e))
            return redirect('cobrar_comanda', comanda_id=comanda_id)

        metodos = request.POST.getlist('metodo[]')
        if metodos:
            try:
                montos = request.POST.getlist('monto[]')
                vueltos = request.POST.getlist('vuelto[]')
                referencias = request.POST.getlist('referencia[]')
                pagos_lista = []
                for i in range(len(metodos)):
                    pagos_lista.append({
                        'metodo': metodos[i],
                        'monto': montos[i] if i < len(montos) else '0',
                        'vuelto': vueltos[i] if i < len(vueltos) else '0',
                        'referencia': referencias[i] if i < len(referencias) else '',
                    })
                comanda.pagar_split(pagos_lista, caja=caja_activa)
                messages.success(request, 'Pago dividido registrado correctamente')
                return redirect('dashboard')
            except ValidationError as e:
                for msg in getattr(e, 'message_dict', [str(e)]):
                    messages.error(request, str(msg))
        else:
            try:
                comanda.pagar(
                    metodo=request.POST.get('metodo'),
                    monto=request.POST.get('monto'),
                    vuelto=request.POST.get('vuelto', 0),
                    referencia=request.POST.get('referencia', ''),
                    caja=caja_activa,
                )
                messages.success(request, 'Pago registrado correctamente')
                return redirect('dashboard')
            except ValidationError as e:
                messages.error(request, str(e))
    return render(request, 'caja/cobrar_comanda.html', {
        'comanda': comanda,
        'metodos': Pago.METODOS,
    })

@login_required
@user_passes_test(es_cajero_o_admin)
def lista_comandas_cobro(request):
    comandas = Comanda.objects.filter(
        estado__in=['ABIERTA', 'LISTA']
    ).select_related('mesa', 'mozo').order_by('-fecha_apertura')
    try:
        caja_abierta = CajaService.obtener_activa()
    except CajaNoAbierta:
        caja_abierta = None
    return render(request, 'caja/lista_comandas_cobro.html', {
        'comandas': comandas,
        'caja_abierta': caja_abierta,
    })

@login_required
@user_passes_test(es_cajero_o_admin)
def apertura_turno(request):
    try:
        caja_abierta = CajaService.obtener_activa()
    except CajaNoAbierta:
        caja_abierta = None

    if request.method == 'POST':
        if 'abrir' in request.POST:
            try:
                CajaService.abrir_turno(
                    turno_nombre=request.POST.get('turno'),
                    usuario=request.user,
                    saldo_inicial=request.POST.get('saldo_inicial', 0),
                )
                messages.success(request, 'Turno abierto')
            except ReglaNegocioViolada as e:
                messages.error(request, str(e))
        elif 'cerrar' in request.POST and caja_abierta:
            try:
                resultado = CajaService.cerrar_turno(caja_abierta.id)
                messages.success(request, f'Turno cerrado. Ventas: S/ {resultado["total_ventas"]}')
            except (RecursoNoEncontrado, ReglaNegocioViolada) as e:
                messages.error(request, str(e))
        return redirect('apertura_turno')
    return render(request, 'caja/apertura_turno.html', {'caja': caja_abierta})

@login_required
@user_passes_test(es_cajero_o_admin)
def reportes_turno(request):
    caja_id = request.GET.get('caja_id')
    fecha_desde = request.GET.get('fecha_desde')
    fecha_hasta = request.GET.get('fecha_hasta')
    reporte = PagoService.reporte_ventas(caja_id, fecha_desde, fecha_hasta)
    cajas = CajaService.listar_todas()
    pagos = Pago.objects.select_related('comanda__mesa', 'comanda__mozo', 'caja').all()
    if caja_id:
        pagos = pagos.filter(caja_id=caja_id)
    if fecha_desde:
        pagos = pagos.filter(fecha__date__gte=fecha_desde)
    if fecha_hasta:
        pagos = pagos.filter(fecha__date__lte=fecha_hasta)
    pagos = pagos[:50]
    return render(request, 'reportes/reportes_turno.html', {
        'reporte': reporte,
        'cajas': cajas,
        'pagos': pagos,
        'ticket_promedio': reporte['ticket_promedio'],
    })

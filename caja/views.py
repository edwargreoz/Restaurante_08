
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from core.rol_utils import es_mozo_o_cajero, es_cajero
from core.excepciones import CajaNoAbierta, RecursoNoEncontrado, ReglaNegocioViolada
from caja.models import Pago
from infraestructura.container import get_container


@login_required
@user_passes_test(es_cajero)
def cobrar_comanda(request, comanda_id):
    try:
        container = get_container()
        comanda = container.pago_service.obtener_comanda_para_cobro(comanda_id)
    except RecursoNoEncontrado as e:
        messages.error(request, str(e))
        return redirect('lista_comandas_cobro')
    if request.method == 'POST':
        try:
            container = get_container()
            caja_activa = container.caja_service.obtener_activa()
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
                container.pago_service.procesar_pago_split(comanda, pagos_lista, caja=caja_activa)
                messages.success(request, 'Pago dividido registrado correctamente')
                return redirect('dashboard')
            except (ReglaNegocioViolada, RecursoNoEncontrado) as e:
                messages.error(request, str(e))
        else:
            try:
                container.pago_service.procesar_pago(
                    comanda,
                    metodo=request.POST.get('metodo'),
                    monto=request.POST.get('monto'),
                    vuelto=request.POST.get('vuelto', 0),
                    referencia=request.POST.get('referencia', ''),
                    caja=caja_activa,
                )
                messages.success(request, 'Pago registrado correctamente')
                return redirect('dashboard')
            except (ReglaNegocioViolada, RecursoNoEncontrado) as e:
                messages.error(request, str(e))
    return render(request, 'caja/cobrar_comanda.html', {
        'comanda': comanda,
        'metodos': Pago.METODOS,
    })

@login_required
@user_passes_test(es_cajero)
def lista_comandas_cobro(request):
    container = get_container()
    comandas = container.pago_service.listar_comandas_para_cobro()
    try:
        container = get_container()
        caja_abierta = container.caja_service.obtener_activa()
    except CajaNoAbierta:
        caja_abierta = None
    return render(request, 'caja/lista_comandas_cobro.html', {
        'comandas': comandas,
        'turno_abierto': caja_abierta,
    })

@login_required
@user_passes_test(es_cajero)
def apertura_turno(request):
    try:
        container = get_container()
        caja_abierta = container.caja_service.obtener_activa()
    except CajaNoAbierta:
        caja_abierta = None

    if request.method == 'POST':
        if 'abrir' in request.POST:
            try:
                container.caja_service.abrir_turno(
                    turno_nombre=request.POST.get('turno'),
                    usuario=request.user,
                    saldo_inicial=request.POST.get('saldo_inicial', 0),
                )
                messages.success(request, 'Turno abierto')
            except ReglaNegocioViolada as e:
                messages.error(request, str(e))
        elif 'cerrar' in request.POST and caja_abierta:
            try:
                resultado = container.caja_service.cerrar_turno(caja_abierta.id)
                messages.success(request, f'Turno cerrado. Ventas: S/ {resultado["total_ventas"]}')
            except (RecursoNoEncontrado, ReglaNegocioViolada) as e:
                messages.error(request, str(e))
        return redirect('apertura_turno')
    return render(request, 'caja/apertura_turno.html', {'caja': caja_abierta})

@login_required
@user_passes_test(es_cajero)
def reportes_turno(request):
    caja_id = request.GET.get('caja_id')
    fecha_desde = request.GET.get('fecha_desde')
    fecha_hasta = request.GET.get('fecha_hasta')
    container = get_container()
    reporte = container.pago_service.reporte_ventas(caja_id, fecha_desde, fecha_hasta)
    cajas = container.caja_service.listar_todas()
    pagos = container.pago_service.listar_pagos_con_filtros(caja_id, fecha_desde, fecha_hasta)
    return render(request, 'reportes/reportes_turno.html', {
        'reporte': reporte,
        'cajas': cajas,
        'pagos': pagos,
        'ticket_promedio': reporte['ticket_promedio'],
    })

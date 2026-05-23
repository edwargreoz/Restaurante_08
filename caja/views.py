
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.utils import timezone
from pedidos.models import Comanda
from caja.models import Caja, Pago
from core.rol_utils import es_mozo_o_cajero, es_cajero_o_admin

@login_required
@user_passes_test(es_mozo_o_cajero)
def cobrar_comanda(request, comanda_id):
    comanda = get_object_or_404(
        Comanda.objects.prefetch_related('lineas__plato', 'pagos'),
        id=comanda_id, estado__in=['ABIERTA', 'LISTA']
    )
    if request.method == 'POST':
        caja_activa = Caja.objects.filter(estado='ABIERTA').first()
        if not caja_activa:
            messages.error(request, 'No hay un turno de caja abierto')
            return redirect('cobrar_comanda', comanda_id=comanda_id)

        metodos = request.POST.getlist('metodo[]')
        if metodos and len(metodos) > 1:
            try:
                pagos_lista = []
                for i in range(len(metodos)):
                    pagos_lista.append({
                        'metodo': metodos[i],
                        'monto': request.POST.getlist('monto[]')[i],
                        'vuelto': request.POST.getlist('vuelto[]', ['0'])[i],
                        'referencia': request.POST.getlist('referencia[]', [''])[i],
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
    caja_abierta = Caja.objects.filter(estado='ABIERTA').first()
    return render(request, 'caja/lista_comandas_cobro.html', {
        'comandas': comandas,
        'caja_abierta': caja_abierta,
    })
@login_required
@user_passes_test(es_cajero_o_admin)
def apertura_turno(request):
    caja_abierta = Caja.objects.filter(estado='ABIERTA').first()
    if request.method == 'POST':
        if 'abrir' in request.POST:
            Caja.objects.create(
                turno=request.POST.get('turno'),
                cajero=request.user,
                saldo_inicial=request.POST.get('saldo_inicial', 0),
            )
            messages.success(request, 'Turno abierto')
        elif 'cerrar' in request.POST:
            if caja_abierta:
                caja_abierta.estado = 'CERRADA'
                caja_abierta.fecha_cierre = timezone.now()
                caja_abierta.save()
                messages.success(request, 'Turno cerrado')
        return redirect('apertura_turno')
    return render(request, 'caja/apertura_turno.html', {'caja': caja_abierta})
    
@login_required
@user_passes_test(es_cajero_o_admin)
def reportes_turno(request):
    caja_id = request.GET.get('caja_id')
    fecha_desde = request.GET.get('fecha_desde')
    fecha_hasta = request.GET.get('fecha_hasta')
    reporte = Pago.objects.reporte_ventas(caja_id, fecha_desde, fecha_hasta)
    cajas = Caja.objects.all()
    pagos = Pago.objects.select_related('comanda__mesa', 'comanda__mozo', 'caja').all()
    if caja_id:
        pagos = pagos.filter(caja_id=caja_id)
    if fecha_desde:
        pagos = pagos.filter(fecha__date__gte=fecha_desde)
    if fecha_hasta:
        pagos = pagos.filter(fecha__date__lte=fecha_hasta)
    pagos = pagos[:50]
    for item in reporte['por_metodo']:
        if reporte['total_general']:
            item['porcentaje'] = int(item['total'] / reporte['total_general'] * 100)
        else:
            item['porcentaje'] = 0
    ticket_promedio = 0
    if reporte['total_pagos']:
        ticket_promedio = reporte['total_general'] / reporte['total_pagos']
    return render(request, 'reportes/reportes_turno.html', {
        'reporte': reporte,
        'cajas': cajas,
        'pagos': pagos,
        'ticket_promedio': ticket_promedio,
    })


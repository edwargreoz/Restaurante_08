from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from core.rol_utils import es_mozo, es_admin
from core.excepciones import (
    RecursoNoEncontrado, CapacidadExcedida, ReglaNegocioViolada,
)
from mesas.models import Mesa
from .models import Reserva
from infraestructura.container import get_container


@login_required
@user_passes_test(es_mozo)
def lista_reservas(request):
    reservas = Reserva.activos.select_related(
        'mesa', 'creado_por', 'union_mesa'
    ).prefetch_related('union_mesa__mesas').all()
    return render(request, 'reservas/lista_reservas.html', {'reservas': reservas})


@login_required
@user_passes_test(es_mozo)
def crear_reserva(request):
    mesas = Mesa.activos.filter(estado='LIBRE')

    if request.method == 'POST':
        try:
            container = get_container()
            reserva = container.reserva_service.crear(
                mesas_ids=request.POST.getlist('mesas_ids'),
                fecha=request.POST.get('fecha'),
                hora_inicio=request.POST.get('hora_inicio'),
                hora_fin=request.POST.get('hora_fin'),
                num_personas=int(request.POST.get('num_personas', 0)),
                cliente_nombre=request.POST.get('cliente_nombre'),
                cliente_contacto=request.POST.get('cliente_contacto', '').strip(),
                observacion=request.POST.get('observacion', ''),
                usuario=request.user,
            )
            msg = f'Reserva creada para {reserva.cliente_nombre}'
            if reserva.union_mesa:
                msg += ' en Unión de Mesas'
            elif reserva.mesa:
                msg += f' en Mesa {reserva.mesa.numero}'
            messages.success(request, msg)
            return redirect('lista_reservas')
        except (ReglaNegocioViolada, CapacidadExcedida, ValueError, TypeError) as e:
            messages.error(request, str(e))
            return render(request, 'reservas/crear_reserva.html', {
                'mesas': mesas, 'datos': request.POST,
            })

    return render(request, 'reservas/crear_reserva.html', {'mesas': mesas})


@login_required
@user_passes_test(es_mozo)
def cancelar_reserva(request, reserva_id):
    if request.method == 'POST':
        try:
            container = get_container()
            container.reserva_service.cancelar(reserva_id)
            messages.success(request, 'Reserva cancelada correctamente')
        except (RecursoNoEncontrado, ReglaNegocioViolada) as e:
            messages.error(request, str(e))
    return redirect('lista_reservas')


@login_required
@user_passes_test(es_mozo)
def finalizar_reserva(request, reserva_id):
    if request.method == 'POST':
        try:
            container = get_container()
            container.reserva_service.finalizar(reserva_id)
            messages.success(request, 'Reserva finalizada correctamente')
        except (RecursoNoEncontrado, ReglaNegocioViolada) as e:
            messages.error(request, str(e))
    return redirect('lista_reservas')


@login_required
@user_passes_test(es_admin)
def eliminar_reserva(request, reserva_id):
    if request.method == 'POST':
        try:
            container = get_container()
            container.reserva_service.eliminar_definitivamente(reserva_id)
            messages.success(request, 'Reserva eliminada permanentemente')
        except (RecursoNoEncontrado, ReglaNegocioViolada) as e:
            messages.error(request, str(e))
    return redirect('lista_reservas')


@login_required
@user_passes_test(es_mozo)
def editar_reserva(request, reserva_id):
    container = get_container()
    try:
        datos_edicion = container.reserva_service.obtener_datos_edicion(reserva_id)
    except RecursoNoEncontrado as e:
        messages.error(request, str(e))
        return redirect('lista_reservas')

    reserva = datos_edicion['reserva']
    mesas = datos_edicion['mesas']
    mesas_actuales_ids = datos_edicion['mesas_actuales_ids']

    if not reserva.activo:
        messages.error(request, 'No puedes editar una reserva cancelada.')
        return redirect('lista_reservas')

    if request.method == 'POST':
        try:
            container.reserva_service.editar(
                reserva_id=reserva_id,
                mesas_ids=request.POST.getlist('mesas_ids'),
                fecha=request.POST.get('fecha'),
                hora_inicio=request.POST.get('hora_inicio'),
                hora_fin=request.POST.get('hora_fin'),
                num_personas=int(request.POST.get('num_personas', 0)),
                cliente_nombre=request.POST.get('cliente_nombre'),
                cliente_contacto=request.POST.get('cliente_contacto', '').strip(),
                observacion=request.POST.get('observacion', ''),
                usuario=request.user,
            )
            messages.success(request, 'Reserva actualizada con éxito')
            return redirect('lista_reservas')

        except (ReglaNegocioViolada, CapacidadExcedida, ValueError, TypeError) as e:
            messages.error(request, str(e))
            return render(request, 'reservas/editar_reserva.html', {
                'mesas': mesas, 'datos': request.POST,
                'reserva': reserva, 'mesas_actuales_ids': mesas_actuales_ids,
            })

    datos = {
        'fecha': reserva.fecha.strftime('%Y-%m-%d'),
        'hora_inicio': reserva.hora_inicio.strftime('%H:%M'),
        'hora_fin': reserva.hora_fin.strftime('%H:%M'),
        'num_personas': reserva.num_personas,
        'cliente_nombre': reserva.cliente_nombre,
        'cliente_contacto': reserva.cliente_contacto,
        'observacion': reserva.observacion,
    }

    return render(request, 'reservas/editar_reserva.html', {
        'mesas': mesas,
        'datos': datos,
        'reserva': reserva,
        'mesas_actuales_ids': [str(x) for x in mesas_actuales_ids],
    })


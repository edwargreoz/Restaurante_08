from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from core.rol_utils import es_mozo, es_admin
from core.excepciones import (
    RecursoNoEncontrado, CapacidadExcedida, ReglaNegocioViolada,
)
from mesas.models import Mesa
from .models import Reserva
from .services import ReservaService


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
            reserva = ReservaService.crear(
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
            ReservaService.cancelar(reserva_id)
            messages.success(request, 'Reserva cancelada correctamente')
        except (RecursoNoEncontrado, ReglaNegocioViolada) as e:
            messages.error(request, str(e))
    return redirect('lista_reservas')


@login_required
@user_passes_test(es_mozo)
def finalizar_reserva(request, reserva_id):
    if request.method == 'POST':
        try:
            ReservaService.finalizar(reserva_id)
            messages.success(request, 'Reserva finalizada correctamente')
        except (RecursoNoEncontrado, ReglaNegocioViolada) as e:
            messages.error(request, str(e))
    return redirect('lista_reservas')


@login_required
@user_passes_test(es_admin)
def eliminar_reserva(request, reserva_id):
    reserva = get_object_or_404(Reserva, id=reserva_id)

    if reserva.activo:
        messages.error(request, 'No puedes eliminar una reserva que todavía está activo. Debes cancelarla primero.')
        return redirect('lista_reservas')

    if request.method == 'POST':
        if reserva.mesa and reserva.mesa.estado == 'RESERVADA':
            reserva.mesa.estado = 'LIBRE'
            reserva.mesa.save(update_fields=['estado'])
        elif reserva.union_mesa:
            for m in reserva.union_mesa.mesas.all():
                if m.estado == 'RESERVADA':
                    m.estado = 'LIBRE'
                    m.save(update_fields=['estado'])
            if reserva.union_mesa.activo:
                reserva.union_mesa.activo = False
                reserva.union_mesa.save(update_fields=['activo'])
        reserva.delete()
        messages.success(request, f'Reserva de {reserva.cliente_nombre} eliminada permanentemente')
    return redirect('lista_reservas')


@login_required
@user_passes_test(es_mozo)
def editar_reserva(request, reserva_id):
    reserva = get_object_or_404(Reserva, id=reserva_id)

    if not reserva.activo:
        messages.error(request, 'No puedes editar una reserva cancelada.')
        return redirect('lista_reservas')

    mesas_actuales_ids = []
    if reserva.mesa:
        mesas_actuales_ids.append(reserva.mesa.id)
    elif reserva.union_mesa:
        mesas_actuales_ids = [m.id for m in reserva.union_mesa.mesas.all()]

    from django.db.models import Q
    mesas = Mesa.activos.filter(Q(estado='LIBRE') | Q(id__in=mesas_actuales_ids))

    if request.method == 'POST':
        try:
            datos = ReservaService._validar_datos(
                mesas_ids=request.POST.getlist('mesas_ids'),
                fecha=request.POST.get('fecha'),
                hora_inicio=request.POST.get('hora_inicio'),
                hora_fin=request.POST.get('hora_fin'),
                num_personas=int(request.POST.get('num_personas', 0)),
                cliente_nombre=request.POST.get('cliente_nombre'),
                cliente_contacto=request.POST.get('cliente_contacto', '').strip(),
                observacion=request.POST.get('observacion', ''),
                mesas_actuales_ids=mesas_actuales_ids,
            )

            ms = datos['mesas']
            vieja_mesa = reserva.mesa
            vieja_union = reserva.union_mesa

            if len(ms) == 1:
                reserva.mesa = ms.first()
                reserva.union_mesa = None
            else:
                from mesas.models import UnionMesa
                union_mesa_obj = UnionMesa.objects.create(activo=True)
                union_mesa_obj.mesas.set(ms)
                union_mesa_obj.save()
                reserva.mesa = None
                reserva.union_mesa = union_mesa_obj

            reserva.cliente_nombre = datos['cliente_nombre']
            reserva.cliente_contacto = datos['cliente_contacto']
            reserva.fecha = datos['fecha']
            reserva.hora_inicio = datos['hora_inicio']
            reserva.hora_fin = datos['hora_fin']
            reserva.num_personas = datos['num_personas']
            reserva.observacion = datos['observacion']
            reserva.save()

            if vieja_mesa and vieja_mesa != reserva.mesa:
                vieja_mesa.estado = 'LIBRE'
                vieja_mesa.save(update_fields=['estado'])
            if vieja_union and vieja_union != reserva.union_mesa:
                vieja_union.activo = False
                vieja_union.save(update_fields=['activo'])
                for m in vieja_union.mesas.all():
                    if m not in ms:
                        m.estado = 'LIBRE'
                        m.save(update_fields=['estado'])

            for m in ms:
                m.estado = 'RESERVADA'
                m.save(update_fields=['estado'])

            messages.success(request, f'Reserva de {reserva.cliente_nombre} actualizada con éxito')
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

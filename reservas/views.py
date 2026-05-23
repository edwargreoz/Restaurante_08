from datetime import time as time_obj, datetime
import re

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db import IntegrityError
from django.core.exceptions import ValidationError
from core.rol_utils import es_mozo, es_admin
from mesas.models import Mesa, UnionMesa
from .models import Reserva


def _validar_datos_reserva(mesas_ids, fecha, hora_inicio, hora_fin,
                           num_personas, cliente_nombre, cliente_contacto,
                           observacion, mesas_actuales_ids=None):
    """
    Valida los datos comunes de crear/editar reserva.
    Retorna un dict con datos validados o renderiza error.
    """
    if not mesas_ids:
        return None, 'Debe seleccionar al menos una mesa'

    mesas_seleccionadas = Mesa.objects.filter(id__in=mesas_ids)
    if mesas_seleccionadas.count() != len(mesas_ids):
        return None, 'Algunas mesas seleccionadas no existen'

    zonas = set(m.zona for m in mesas_seleccionadas)
    if len(zonas) > 1:
        return None, 'No puedes unir mesas de diferentes zonas (ej. Salón y Terraza)'

    for m in mesas_seleccionadas:
        if mesas_actuales_ids and m.id in mesas_actuales_ids:
            continue
        if m.estado != 'LIBRE':
            return None, f'La mesa {m.numero} no está disponible'

    capacidad_total = sum(m.capacidad for m in mesas_seleccionadas)
    num_per_int = int(num_personas)
    if num_per_int > capacidad_total:
        if len(mesas_seleccionadas) > 1:
            return None, f'Las mesas seleccionadas solo tienen capacidad conjunta para {capacidad_total} personas'
        return None, f'La mesa seleccionada solo tiene capacidad para {capacidad_total} personas'

    if len(mesas_seleccionadas) > 1:
        for m in mesas_seleccionadas:
            if (capacidad_total - m.capacidad) >= num_per_int:
                return None, 'Has seleccionado más mesas de las necesarias.'

    try:
        inicio = datetime.strptime(hora_inicio, '%H:%M').time()
        fin = datetime.strptime(hora_fin, '%H:%M').time()
    except (ValueError, TypeError):
        return None, 'Formato de hora inválido'

    if inicio < time_obj(7, 0) or fin > time_obj(22, 0):
        return None, 'El horario de atención del restaurante es de 07:00 a 22:00'
    if inicio >= fin:
        return None, 'La hora de inicio debe ser anterior a la hora de fin'

    if cliente_contacto:
        if '@' in cliente_contacto:
            if not re.match(r"[^@]+@[^@]+\.[^@]+", cliente_contacto):
                return None, 'El correo electrónico ingresado no es válido'
        else:
            if not cliente_contacto.isdigit() or len(cliente_contacto) != 9:
                return None, 'El número de celular debe contener exactamente 9 dígitos'

    return {
        'mesas_seleccionadas': mesas_seleccionadas,
        'num_per_int': num_per_int,
        'cliente_nombre': cliente_nombre,
        'cliente_contacto': cliente_contacto,
        'fecha': fecha,
        'hora_inicio': hora_inicio,
        'hora_fin': hora_fin,
        'observacion': observacion,
    }, None


@login_required
@user_passes_test(es_mozo)
def lista_reservas(request):
    reservas = Reserva.objects.select_related(
        'mesa', 'creado_por', 'union_mesa'
    ).prefetch_related('union_mesa__mesas').all()
    return render(request, 'reservas/lista_reservas.html', {'reservas': reservas})


@login_required
@user_passes_test(es_mozo)
def crear_reserva(request):
    mesas = Mesa.objects.filter(estado='LIBRE')

    if request.method == 'POST':
        datos, error = _validar_datos_reserva(
            mesas_ids=request.POST.getlist('mesas_ids'),
            fecha=request.POST.get('fecha'),
            hora_inicio=request.POST.get('hora_inicio'),
            hora_fin=request.POST.get('hora_fin'),
            num_personas=request.POST.get('num_personas'),
            cliente_nombre=request.POST.get('cliente_nombre'),
            cliente_contacto=request.POST.get('cliente_contacto', '').strip(),
            observacion=request.POST.get('observacion', ''),
        )
        if error:
            messages.error(request, error)
            return render(request, 'reservas/crear_reserva.html', {'mesas': mesas, 'datos': request.POST})

        try:
            ms = datos['mesas_seleccionadas']
            mesa_obj = ms.first() if len(ms) == 1 else None
            union_mesa_obj = None if mesa_obj else UnionMesa.objects.create(activa=True)

            if union_mesa_obj:
                union_mesa_obj.mesas.set(ms)
                union_mesa_obj.save()

            reserva = Reserva.objects.create(
                mesa=mesa_obj,
                union_mesa=union_mesa_obj,
                cliente_nombre=datos['cliente_nombre'],
                cliente_contacto=datos['cliente_contacto'],
                fecha=datos['fecha'],
                hora_inicio=datos['hora_inicio'],
                hora_fin=datos['hora_fin'],
                num_personas=datos['num_per_int'],
                observacion=datos['observacion'],
                creado_por=request.user,
            )

            msg = f'Reserva creada para {reserva.cliente_nombre}'
            if union_mesa_obj:
                msg += ' en Unión de Mesas'
            else:
                msg += f' en Mesa {mesa_obj.numero}'
            messages.success(request, msg)
            return redirect('lista_reservas')

        except (ValueError, TypeError, IntegrityError) as e:
            messages.error(request, f'Error al guardar la reserva: {e}')
            return render(request, 'reservas/crear_reserva.html', {'mesas': mesas, 'datos': request.POST})

    return render(request, 'reservas/crear_reserva.html', {'mesas': mesas})


@login_required
@user_passes_test(es_mozo)
def cancelar_reserva(request, reserva_id):
    reserva = get_object_or_404(Reserva, id=reserva_id)

    if not reserva.activa:
        messages.warning(request, 'Esta reserva ya estaba cancelada')
        return redirect('lista_reservas')

    if request.method == 'POST':
        reserva.cancelar()
        messages.success(request, f'Reserva de {reserva.cliente_nombre} cancelada correctamente')

    return redirect('lista_reservas')


@login_required
@user_passes_test(es_mozo)
def finalizar_reserva(request, reserva_id):
    reserva = get_object_or_404(Reserva, id=reserva_id)

    if not reserva.activa:
        messages.warning(request, 'Esta reserva ya no está activa')
        return redirect('lista_reservas')

    if request.method == 'POST':
        reserva.finalizar()
        messages.success(request, f'Reserva de {reserva.cliente_nombre} finalizada correctamente')

    return redirect('lista_reservas')

@login_required
@user_passes_test(es_admin)
def eliminar_reserva(request, reserva_id):
    reserva = get_object_or_404(Reserva, id=reserva_id)
    
    if reserva.activa:
        messages.error(request, 'No puedes eliminar una reserva que todavía está activa. Debes cancelarla primero.')
        return redirect('lista_reservas')
        
    if request.method == 'POST':
        # Seguridad: liberar mesas si quedaron en estado RESERVADA
        if reserva.mesa and reserva.mesa.estado == 'RESERVADA':
            reserva.mesa.estado = 'LIBRE'
            reserva.mesa.save(update_fields=['estado'])
        elif reserva.union_mesa:
            for m in reserva.union_mesa.mesas.all():
                if m.estado == 'RESERVADA':
                    m.estado = 'LIBRE'
                    m.save(update_fields=['estado'])
            # Desactivar la unión para que las mesas dejen de estar "unidas"
            if reserva.union_mesa.activa:
                reserva.union_mesa.activa = False
                reserva.union_mesa.save(update_fields=['activa'])
        reserva.delete()
        messages.success(request, f'Reserva de {reserva.cliente_nombre} eliminada permanentemente')
    return redirect('lista_reservas')

@login_required
@user_passes_test(es_mozo)
def editar_reserva(request, reserva_id):
    reserva = get_object_or_404(Reserva, id=reserva_id)

    if not reserva.activa:
        messages.error(request, 'No puedes editar una reserva cancelada.')
        return redirect('lista_reservas')

    mesas_actuales_ids = []
    if reserva.mesa:
        mesas_actuales_ids.append(reserva.mesa.id)
    elif reserva.union_mesa:
        mesas_actuales_ids = [m.id for m in reserva.union_mesa.mesas.all()]

    from django.db.models import Q
    mesas = Mesa.objects.filter(Q(estado='LIBRE') | Q(id__in=mesas_actuales_ids))

    if request.method == 'POST':
        datos, error = _validar_datos_reserva(
            mesas_ids=request.POST.getlist('mesas_ids'),
            fecha=request.POST.get('fecha'),
            hora_inicio=request.POST.get('hora_inicio'),
            hora_fin=request.POST.get('hora_fin'),
            num_personas=request.POST.get('num_personas'),
            cliente_nombre=request.POST.get('cliente_nombre'),
            cliente_contacto=request.POST.get('cliente_contacto', '').strip(),
            observacion=request.POST.get('observacion', ''),
            mesas_actuales_ids=mesas_actuales_ids,
        )
        if error:
            messages.error(request, error)
            return render(request, 'reservas/editar_reserva.html', {
                'mesas': mesas, 'datos': request.POST,
                'reserva': reserva, 'mesas_actuales_ids': mesas_actuales_ids,
            })

        try:
            ms = datos['mesas_seleccionadas']
            vieja_mesa = reserva.mesa
            vieja_union = reserva.union_mesa

            if len(ms) == 1:
                reserva.mesa = ms.first()
                reserva.union_mesa = None
            else:
                union_mesa_obj = UnionMesa.objects.create(activa=True)
                union_mesa_obj.mesas.set(ms)
                union_mesa_obj.save()
                reserva.mesa = None
                reserva.union_mesa = union_mesa_obj

            reserva.cliente_nombre = datos['cliente_nombre']
            reserva.cliente_contacto = datos['cliente_contacto']
            reserva.fecha = datos['fecha']
            reserva.hora_inicio = datos['hora_inicio']
            reserva.hora_fin = datos['hora_fin']
            reserva.num_personas = datos['num_per_int']
            reserva.observacion = datos['observacion']
            reserva.save()

            if vieja_mesa and vieja_mesa != reserva.mesa:
                vieja_mesa.estado = 'LIBRE'
                vieja_mesa.save(update_fields=['estado'])
            if vieja_union and vieja_union != reserva.union_mesa:
                vieja_union.activa = False
                vieja_union.save(update_fields=['activa'])
                for m in vieja_union.mesas.all():
                    if m not in ms:
                        m.estado = 'LIBRE'
                        m.save(update_fields=['estado'])
            
            # Asegurar que todas las mesas de la nueva reserva cambien a RESERVADA
            for m in ms:
                m.estado = 'RESERVADA'
                m.save(update_fields=['estado'])

            messages.success(request, f'Reserva de {reserva.cliente_nombre} actualizada con éxito')
            return redirect('lista_reservas')

        except (ValueError, TypeError, IntegrityError) as e:
            messages.error(request, f'Error al guardar la reserva: {e}')
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
        'mesas_actuales_ids': [str(x) for x in mesas_actuales_ids]
    })

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db import IntegrityError
from django.core.exceptions import ValidationError
from core.rol_utils import es_mozo, es_admin
from mesas.models import Mesa, UnionMesa
from .models import Reserva


@login_required
@user_passes_test(es_mozo)
def lista_reservas(request):
    reservas = Reserva.objects.select_related('mesa', 'creado_por').all()
    return render(request, 'reservas/lista_reservas.html', {'reservas': reservas})


@login_required
@user_passes_test(es_mozo)
def crear_reserva(request):
    mesas = Mesa.objects.filter(estado='LIBRE')
    
    if request.method == 'POST':
        mesas_ids = request.POST.getlist('mesas_ids')
        fecha = request.POST.get('fecha')
        hora_inicio = request.POST.get('hora_inicio')
        hora_fin = request.POST.get('hora_fin')
        num_personas = request.POST.get('num_personas')
        cliente_nombre = request.POST.get('cliente_nombre')
        cliente_contacto = request.POST.get('cliente_contacto', '').strip()
        observacion = request.POST.get('observacion', '')

        def _render_error(msg):
            messages.error(request, msg)
            return render(request, 'reservas/crear_reserva.html', {'mesas': mesas, 'datos': request.POST})

        if not mesas_ids:
            return _render_error('Debe seleccionar al menos una mesa')

        try:
            mesas_seleccionadas = Mesa.objects.filter(id__in=mesas_ids)
            
            if mesas_seleccionadas.count() != len(mesas_ids):
                return _render_error('Algunas mesas seleccionadas no existen')

            zonas_seleccionadas = set(m.zona for m in mesas_seleccionadas)
            if len(zonas_seleccionadas) > 1:
                return _render_error('No puedes unir mesas de diferentes zonas (ej. Salón y Terraza)')

            for m in mesas_seleccionadas:
                if m.estado != 'LIBRE':
                    return _render_error(f'La mesa {m.numero} no está disponible')

            capacidad_total = sum(m.capacidad for m in mesas_seleccionadas)
            num_per_int = int(num_personas)
            if num_per_int > capacidad_total:
                if len(mesas_seleccionadas) > 1:
                    return _render_error(f'Las mesas seleccionadas solo tienen capacidad conjunta para {capacidad_total} personas')
                else:
                    return _render_error(f'La mesa seleccionada solo tiene capacidad para {capacidad_total} personas')

            if len(mesas_seleccionadas) > 1:
                for m in mesas_seleccionadas:
                    if (capacidad_total - m.capacidad) >= num_per_int:
                        return _render_error('Has seleccionado más mesas de las necesarias. No puedes exceder la capacidad requerida reservando mesas extra.')

            if hora_inicio < "07:00" or hora_fin > "22:00":
                return _render_error('El horario de atención del restaurante es de 07:00 a 22:00')

            if hora_inicio >= hora_fin:
                return _render_error('La hora de inicio debe ser anterior a la hora de fin')

            if cliente_contacto:
                import re
                if '@' in cliente_contacto:
                    if not re.match(r"[^@]+@[^@]+\.[^@]+", cliente_contacto):
                        return _render_error('El correo electrónico ingresado no es válido')
                else:
                    if not cliente_contacto.isdigit() or len(cliente_contacto) != 9:
                        return _render_error('El número de celular debe contener exactamente 9 dígitos numéricos')

            mesa_obj = None
            union_mesa_obj = None

            if len(mesas_seleccionadas) == 1:
                mesa_obj = mesas_seleccionadas.first()
            else:
                union_mesa_obj = UnionMesa.objects.create(activa=True)
                union_mesa_obj.mesas.set(mesas_seleccionadas)
                union_mesa_obj.save()

            reserva = Reserva.objects.create(
                mesa=mesa_obj,
                union_mesa=union_mesa_obj,
                cliente_nombre=cliente_nombre,
                cliente_contacto=cliente_contacto,
                fecha=fecha,
                hora_inicio=hora_inicio,
                hora_fin=hora_fin,
                num_personas=num_personas,
                observacion=observacion,
                creado_por=request.user,
            )

            if union_mesa_obj:
                messages.success(request, f'Reserva creada para {reserva.cliente_nombre} en Unión de Mesas')
            else:
                messages.success(request, f'Reserva creada para {reserva.cliente_nombre} en Mesa {mesa_obj.numero}')
            return redirect('lista_reservas')

        except (ValueError, TypeError):
            return _render_error('Verifica que todos los datos sean correctos')
        except IntegrityError:
            return _render_error('Error al guardar la reserva')
        except Exception as e:
            return _render_error(f'Ocurrio un error: {str(e)}')

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
        mesas_ids = request.POST.getlist('mesas_ids')
        fecha = request.POST.get('fecha')
        hora_inicio = request.POST.get('hora_inicio')
        hora_fin = request.POST.get('hora_fin')
        num_personas = request.POST.get('num_personas')
        cliente_nombre = request.POST.get('cliente_nombre')
        cliente_contacto = request.POST.get('cliente_contacto', '').strip()
        observacion = request.POST.get('observacion', '')

        def _render_error(msg):
            messages.error(request, msg)
            return render(request, 'reservas/editar_reserva.html', {'mesas': mesas, 'datos': request.POST, 'reserva': reserva, 'mesas_actuales_ids': mesas_ids})

        if not mesas_ids:
            return _render_error('Debe seleccionar al menos una mesa')

        try:
            mesas_seleccionadas = Mesa.objects.filter(id__in=mesas_ids)
            
            if mesas_seleccionadas.count() != len(mesas_ids):
                return _render_error('Algunas mesas seleccionadas no existen')

            zonas_seleccionadas = set(m.zona for m in mesas_seleccionadas)
            if len(zonas_seleccionadas) > 1:
                return _render_error('No puedes unir mesas de diferentes zonas (ej. Salón y Terraza)')

            for m in mesas_seleccionadas:
                if m.estado != 'LIBRE' and m.id not in mesas_actuales_ids:
                    return _render_error(f'La mesa {m.numero} no está disponible')

            capacidad_total = sum(m.capacidad for m in mesas_seleccionadas)
            num_per_int = int(num_personas)
            if num_per_int > capacidad_total:
                return _render_error(f'La capacidad conjunta seleccionada es {capacidad_total}, insuficiente para {num_personas} personas')

            if len(mesas_seleccionadas) > 1:
                for m in mesas_seleccionadas:
                    if (capacidad_total - m.capacidad) >= num_per_int:
                        return _render_error('Has seleccionado más mesas de las necesarias. No puedes exceder la capacidad requerida reservando mesas extra.')

            if hora_inicio < "07:00" or hora_fin > "22:00":
                return _render_error('El horario de atención del restaurante es de 07:00 a 22:00')

            if hora_inicio >= hora_fin:
                return _render_error('La hora de inicio debe ser anterior a la hora de fin')

            if cliente_contacto:
                import re
                if '@' in cliente_contacto:
                    if not re.match(r"[^@]+@[^@]+\.[^@]+", cliente_contacto):
                        return _render_error('El correo electrónico ingresado no es válido')
                else:
                    if not cliente_contacto.isdigit() or len(cliente_contacto) != 9:
                        return _render_error('El número de celular debe contener exactamente 9 dígitos numéricos')

            vieja_mesa = reserva.mesa
            vieja_union = reserva.union_mesa
            
            mesa_obj = None
            union_mesa_obj = None

            if len(mesas_seleccionadas) == 1:
                mesa_obj = mesas_seleccionadas.first()
            else:
                union_mesa_obj = UnionMesa.objects.create(activa=True)
                union_mesa_obj.mesas.set(mesas_seleccionadas)
                union_mesa_obj.save()

            reserva.mesa = mesa_obj
            reserva.union_mesa = union_mesa_obj
            reserva.cliente_nombre = cliente_nombre
            reserva.cliente_contacto = cliente_contacto
            reserva.fecha = fecha
            reserva.hora_inicio = hora_inicio
            reserva.hora_fin = hora_fin
            reserva.num_personas = num_personas
            reserva.observacion = observacion
            reserva.save() 
            
            if vieja_mesa and vieja_mesa != mesa_obj and vieja_mesa not in mesas_seleccionadas:
                vieja_mesa.estado = 'LIBRE'
                vieja_mesa.save(update_fields=['estado'])
            
            if vieja_union and vieja_union != union_mesa_obj:
                for m in vieja_union.mesas.all():
                    if m not in mesas_seleccionadas:
                        m.estado = 'LIBRE'
                        m.save(update_fields=['estado'])
                vieja_union.activa = False
                vieja_union.save(update_fields=['activa'])

            messages.success(request, f'Reserva de {reserva.cliente_nombre} actualizada con éxito')
            return redirect('lista_reservas')

        except (ValueError, TypeError):
            return _render_error('Verifica que todos los datos sean correctos')
        except IntegrityError:
            return _render_error('Error al guardar la reserva')
        except Exception as e:
            return _render_error(f'Ocurrio un error: {str(e)}')

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

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db import IntegrityError
from django.core.exceptions import ValidationError
from core.rol_utils import es_mozo
from mesas.models import Mesa
from .models import Reserva


@login_required
@user_passes_test(es_mozo)
def lista_reservas(request):
    reservas = Reserva.objects.select_related('mesa', 'creado_por').all()
    return render(request, 'reservas/lista_reservas.html', {'reservas': reservas})


@login_required
@user_passes_test(es_mozo)
def crear_reserva(request):
    if request.method == 'POST':
        mesa_id = request.POST.get('mesa_id')
        fecha = request.POST.get('fecha')
        hora_inicio = request.POST.get('hora_inicio')
        hora_fin = request.POST.get('hora_fin')
        num_personas = request.POST.get('num_personas')

        try:
            mesa = Mesa.objects.get(id=mesa_id)

            if mesa.estado != 'LIBRE':
                messages.error(request, f'La mesa {mesa.numero} no esta disponible')
                return redirect('crear_reserva')

            if int(num_personas) > mesa.capacidad:
                messages.error(request, f'La mesa {mesa.numero} solo tiene capacidad para {mesa.capacidad} personas')
                return redirect('crear_reserva')

            if hora_inicio >= hora_fin:
                messages.error(request, 'La hora de inicio debe ser anterior a la hora de fin')
                return redirect('crear_reserva')

            reserva = Reserva.objects.create(
                mesa=mesa,
                cliente_nombre=request.POST.get('cliente_nombre'),
                cliente_contacto=request.POST.get('cliente_contacto', ''),
                fecha=fecha,
                hora_inicio=hora_inicio,
                hora_fin=hora_fin,
                num_personas=num_personas,
                observacion=request.POST.get('observacion', ''),
                creado_por=request.user,
            )

            messages.success(request, f'Reserva creada para {reserva.cliente_nombre} en Mesa {mesa.numero}')
            return redirect('lista_reservas')

        except Mesa.DoesNotExist:
            messages.error(request, 'La mesa seleccionada no existe')
        except (ValueError, TypeError):
            messages.error(request, 'Verifica que todos los datos sean correctos')
        except IntegrityError:
            messages.error(request, 'Error al guardar la reserva')
        except Exception as e:
            messages.error(request, f'Ocurrio un error: {str(e)}')

        return redirect('crear_reserva')

    mesas = Mesa.objects.filter(estado='LIBRE')
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

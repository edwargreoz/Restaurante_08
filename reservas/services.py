from datetime import time as time_obj, datetime
import re
from django.db import transaction
from core.excepciones import (
    RecursoNoEncontrado, CapacidadExcedida, ReglaNegocioViolada,
)
from reservas.models import Reserva
from mesas.models import Mesa, UnionMesa


class ReservaService:
    HORA_APERTURA = time_obj(7, 0)
    HORA_CIERRE = time_obj(22, 0)

    @staticmethod
    @transaction.atomic
    def crear(mesas_ids: list, fecha, hora_inicio, hora_fin,
              num_personas: int, cliente_nombre: str,
              cliente_contacto: str = '', observacion: str = '',
              usuario=None) -> Reserva:
        datos = ReservaService._validar_datos(
            mesas_ids, fecha, hora_inicio, hora_fin,
            num_personas, cliente_nombre, cliente_contacto, observacion
        )

        ms = datos['mesas']
        mesa_obj = ms.first() if len(ms) == 1 else None
        union_mesa_obj = None if mesa_obj else UnionMesa.objects.create(activa=True)

        if union_mesa_obj:
            union_mesa_obj.mesas.set(ms)
            union_mesa_obj.save()

        reserva = Reserva.objects.create(
            mesa=mesa_obj, union_mesa=union_mesa_obj,
            cliente_nombre=datos['cliente_nombre'],
            cliente_contacto=datos['cliente_contacto'],
            fecha=datos['fecha'], hora_inicio=datos['hora_inicio'],
            hora_fin=datos['hora_fin'],
            num_personas=datos['num_personas'],
            observacion=datos['observacion'], creado_por=usuario,
        )
        return reserva

    @staticmethod
    def cancelar(reserva_id: int) -> Reserva:
        reserva = Reserva.objects.filter(id=reserva_id).first()
        if not reserva:
            raise RecursoNoEncontrado('Reserva no encontrada')
        if not reserva.activa:
            raise ReglaNegocioViolada('Esta reserva ya estaba cancelada')
        reserva.cancelar()
        _notificar_plano()
        return reserva

    @staticmethod
    def finalizar(reserva_id: int) -> Reserva:
        reserva = Reserva.objects.filter(id=reserva_id).first()
        if not reserva:
            raise RecursoNoEncontrado('Reserva no encontrada')
        if not reserva.activa:
            raise ReglaNegocioViolada('Esta reserva ya no está activa')
        reserva.finalizar()
        _notificar_plano()
        return reserva

    @staticmethod
    def _validar_datos(mesas_ids, fecha, hora_inicio, hora_fin,
                       num_personas, cliente_nombre, cliente_contacto,
                       observacion, mesas_actuales_ids=None):
        if not mesas_ids:
            raise ReglaNegocioViolada('Debe seleccionar al menos una mesa')

        ms = Mesa.objects.filter(id__in=mesas_ids)
        if ms.count() != len(mesas_ids):
            raise ReglaNegocioViolada('Algunas mesas no existen')

        zonas = set(m.zona for m in ms)
        if len(zonas) > 1:
            raise ReglaNegocioViolada('No puedes unir mesas de diferentes zonas')

        mesas_actuales_ids = mesas_actuales_ids or []
        for m in ms:
            if m.id in mesas_actuales_ids:
                continue
            if m.estado != 'LIBRE':
                raise ReglaNegocioViolada(f'La mesa {m.numero} no está disponible')

        capacidad = sum(m.capacidad for m in ms)
        if num_personas > capacidad:
            raise CapacidadExcedida(
                f'Solo hay capacidad para {capacidad} personas'
            )

        if len(ms) > 1:
            for m in ms:
                if (capacidad - m.capacidad) >= num_personas:
                    raise CapacidadExcedida(
                        'Has seleccionado más mesas de las necesarias'
                    )

        try:
            inicio = datetime.strptime(hora_inicio, '%H:%M').time()
            fin = datetime.strptime(hora_fin, '%H:%M').time()
        except (ValueError, TypeError):
            raise ReglaNegocioViolada('Formato de hora inválido')

        if inicio < ReservaService.HORA_APERTURA or fin > ReservaService.HORA_CIERRE:
            raise ReglaNegocioViolada('El horario de atención es de 07:00 a 22:00')
        if inicio >= fin:
            raise ReglaNegocioViolada('La hora de inicio debe ser anterior a la hora de fin')

        if cliente_contacto:
            if '@' in cliente_contacto:
                if not re.match(r"[^@]+@[^@]+\.[^@]+", cliente_contacto):
                    raise ReglaNegocioViolada('Correo electrónico inválido')
            else:
                if not cliente_contacto.isdigit() or len(cliente_contacto) != 9:
                    raise ReglaNegocioViolada('El celular debe tener 9 dígitos')

        return {
            'mesas': ms, 'num_personas': num_personas,
            'cliente_nombre': cliente_nombre,
            'cliente_contacto': cliente_contacto,
            'fecha': fecha, 'hora_inicio': hora_inicio,
            'hora_fin': hora_fin, 'observacion': observacion,
        }


def _notificar_plano():
    try:
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_safe
        channel_layer = get_channel_layer()
        async_to_safe(channel_layer.group_send)(
            'plano', {'type': 'plano_update', 'data': {'action': 'refresh'}}
        )
    except Exception:
        pass

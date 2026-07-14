from datetime import time as time_obj, datetime
import re
from django.db import transaction
from core.excepciones import (
    RecursoNoEncontrado, CapacidadExcedida, ReglaNegocioViolada,
)
from reservas.models import Reserva
from mesas.models import Mesa, UnionMesa
from mesas.services import _notificar_plano


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
        union_mesa_obj = None if mesa_obj else UnionMesa.objects.create(activo=True)

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
    @transaction.atomic
    def cancelar(reserva_id: int) -> Reserva:
        reserva = Reserva.objects.filter(id=reserva_id).first()
        if not reserva:
            raise RecursoNoEncontrado('Reserva no encontrada')
        if not reserva.activo:
            raise ReglaNegocioViolada('Esta reserva ya estaba cancelada')
        reserva.cancelar()
        _notificar_plano()
        return reserva

    @staticmethod
    @transaction.atomic
    def finalizar(reserva_id: int) -> Reserva:
        reserva = Reserva.objects.filter(id=reserva_id).first()
        if not reserva:
            raise RecursoNoEncontrado('Reserva no encontrada')
        if not reserva.activo:
            raise ReglaNegocioViolada('Esta reserva ya no está activa')
        reserva.finalizar()
        _notificar_plano()
        return reserva

    @staticmethod
    @transaction.atomic
    def editar(reserva_id: int, mesas_ids: list, fecha, hora_inicio, hora_fin,
               num_personas: int, cliente_nombre: str,
               cliente_contacto: str = '', observacion: str = '',
               usuario=None) -> Reserva:
        reserva = Reserva.objects.filter(id=reserva_id).first()
        if not reserva:
            raise RecursoNoEncontrado('Reserva no encontrada')
        if not reserva.activo:
            raise ReglaNegocioViolada('No puedes editar una reserva cancelada')

        vieja_mesa = reserva.mesa
        vieja_union = reserva.union_mesa

        mesas_actuales_ids = []
        if vieja_mesa:
            mesas_actuales_ids.append(vieja_mesa.id)
        elif vieja_union:
            mesas_actuales_ids = [m.id for m in vieja_union.mesas.all()]

        datos = ReservaService._validar_datos(
            mesas_ids, fecha, hora_inicio, hora_fin,
            num_personas, cliente_nombre, cliente_contacto, observacion,
            mesas_actuales_ids=mesas_actuales_ids,
        )

        ms = datos['mesas']

        if len(ms) == 1:
            reserva.mesa = ms.first()
            reserva.union_mesa = None
        else:
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
        reserva.save(update_fields=[
            'mesa', 'union_mesa', 'cliente_nombre', 'cliente_contacto',
            'fecha', 'hora_inicio', 'hora_fin', 'num_personas',
            'observacion', 'actualizado_en'
        ])

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

        _notificar_plano()
        return reserva

    @staticmethod
    @transaction.atomic
    def eliminar_definitivamente(reserva_id: int) -> None:
        reserva = Reserva.objects.filter(id=reserva_id).first()
        if not reserva:
            raise RecursoNoEncontrado('Reserva no encontrada')
        if reserva.activo:
            raise ReglaNegocioViolada(
                'No puedes eliminar una reserva que todavía está activa. Debes cancelarla primero.'
            )
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
        reserva.eliminar()
        _notificar_plano()

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




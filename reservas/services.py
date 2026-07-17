from datetime import time as time_obj, datetime
import re
from django.db import transaction
from core.excepciones import (
    RecursoNoEncontrado, CapacidadExcedida, ReglaNegocioViolada,
)
from reservas.models import Reserva
from mesas.models import Mesa, UnionMesa
from mesas.services import _notificar_plano



from dominio.puertos.repositorios import IReservaRepository
from typing import Optional


class ReservaService:
    HORA_APERTURA = time_obj(7, 0)
    HORA_CIERRE = time_obj(22, 0)

    def __init__(self, reserva_repo: Optional[IReservaRepository] = None):
        self.reserva_repo = reserva_repo

    def listar(self):
        return self.reserva_repo.listar()

    @transaction.atomic
    def crear(self, mesas_ids: list, fecha, hora_inicio, hora_fin,
              num_personas: int, cliente_nombre: str,
              cliente_contacto: str = '', observacion: str = '',
              usuario=None) -> Reserva:
        datos = self._validar_datos(
            mesas_ids, fecha, hora_inicio, hora_fin,
            num_personas, cliente_nombre, cliente_contacto, observacion
        )
        ms = datos['mesas']
        mesa_obj = ms.first() if len(ms) == 1 else None
        union_mesa_obj = None
        if len(ms) > 1:
            union_mesa_obj = UnionMesa.objects.create(activo=True)
            union_mesa_obj.mesas.set(ms)
            union_mesa_obj.save()

        from dominio.entidades.reserva import Reserva as ReservaDominio
        reserva_domain = ReservaDominio(
            id=None,
            mesa_id=mesa_obj.id if mesa_obj else None,
            union_mesa_id=union_mesa_obj.id if union_mesa_obj else None,
            cliente_nombre=datos['cliente_nombre'],
            fecha=datos['fecha'],
            hora_inicio=datos['hora_inicio'],
            hora_fin=datos['hora_fin'],
            num_personas=datos['num_personas']
        )
        # TODO: Pasar otros campos como observacion y creado_por si el puerto/entidad los soporta
        reserva = self.reserva_repo.guardar(reserva_domain)
        return reserva

    @transaction.atomic
    def cancelar(self, reserva_id: int) -> Reserva:
        reserva = Reserva.objects.select_for_update().filter(id=reserva_id).first()
        if not reserva:
            raise RecursoNoEncontrado('Reserva no encontrada')
        if not reserva.activo:
            raise ReglaNegocioViolada('Esta reserva ya estaba cancelada')

        reserva.activo = False
        reserva.save(update_fields=['activo'])

        if reserva.mesa:
            tiene_otra = Reserva.objects.filter(
                mesa=reserva.mesa, activo=True
            ).exclude(id=reserva.id).exists()
            if not tiene_otra:
                reserva.mesa.estado = 'LIBRE'
                reserva.mesa.save(update_fields=['estado'])
        elif reserva.union_mesa:
            tiene_otra = Reserva.objects.filter(
                union_mesa=reserva.union_mesa, activo=True
            ).exclude(id=reserva.id).exists()
            if not tiene_otra:
                for m in reserva.union_mesa.mesas.all():
                    m.estado = 'LIBRE'
                    m.save(update_fields=['estado'])
                reserva.union_mesa.activo = False
                reserva.union_mesa.save(update_fields=['activo'])

        _notificar_plano()
        return reserva

    @transaction.atomic
    def finalizar(self, reserva_id: int) -> Reserva:
        reserva = Reserva.objects.select_for_update().filter(id=reserva_id).first()
        if not reserva:
            raise RecursoNoEncontrado('Reserva no encontrada')
        if not reserva.activo:
            raise ReglaNegocioViolada('Esta reserva ya no está activa')

        reserva.activo = False
        reserva.finalizada = True
        reserva.save(update_fields=['activo', 'finalizada'])

        if reserva.mesa:
            tiene_otra = Reserva.objects.filter(
                mesa=reserva.mesa, activo=True
            ).exclude(id=reserva.id).exists()
            if not tiene_otra:
                reserva.mesa.estado = 'LIMPIEZA'
                reserva.mesa.save(update_fields=['estado'])
        elif reserva.union_mesa:
            tiene_otra = Reserva.objects.filter(
                union_mesa=reserva.union_mesa, activo=True
            ).exclude(id=reserva.id).exists()
            if not tiene_otra:
                for m in reserva.union_mesa.mesas.all():
                    m.estado = 'LIMPIEZA'
                    m.save(update_fields=['estado'])
                reserva.union_mesa.activo = False
                reserva.union_mesa.save(update_fields=['activo'])

        _notificar_plano()
        return reserva

    @transaction.atomic
    def editar(self, reserva_id: int, mesas_ids: list, fecha,
               hora_inicio, hora_fin, num_personas: int,
               cliente_nombre: str, cliente_contacto: str = '',
               observacion: str = '', usuario=None) -> Reserva:
        reserva = Reserva.objects.select_for_update().filter(id=reserva_id).first()
        if not reserva:
            raise RecursoNoEncontrado('Reserva no encontrada')
        if not reserva.activo:
            raise ReglaNegocioViolada(
                'No puedes editar una reserva cancelada'
            )

        vieja_mesa = reserva.mesa
        vieja_union = reserva.union_mesa

        mesas_actuales_ids = []
        if vieja_mesa:
            mesas_actuales_ids.append(vieja_mesa.id)
        elif vieja_union:
            mesas_actuales_ids = [
                m.id for m in vieja_union.mesas.all()
            ]

        datos = self._validar_datos(
            mesas_ids, fecha, hora_inicio, hora_fin,
            num_personas, cliente_nombre, cliente_contacto,
            observacion, mesas_actuales_ids=mesas_actuales_ids,
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
            'mesa', 'union_mesa', 'cliente_nombre',
            'cliente_contacto', 'fecha', 'hora_inicio',
            'hora_fin', 'num_personas', 'observacion',
            'actualizado_en',
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

    @transaction.atomic
    def eliminar_definitivamente(self, reserva_id: int) -> None:
        reserva = Reserva.objects.select_for_update().filter(id=reserva_id).first()
        if not reserva:
            raise RecursoNoEncontrado('Reserva no encontrada')
        if reserva.activo:
            raise ReglaNegocioViolada(
                'No puedes eliminar una reserva activa. '
                'Debes cancelarla primero.'
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
        reserva.delete()
        _notificar_plano()

    def _validar_datos(self, mesas_ids, fecha, hora_inicio, hora_fin,
                       num_personas, cliente_nombre, cliente_contacto,
                       observacion, mesas_actuales_ids=None):
        if not mesas_ids:
            raise ReglaNegocioViolada(
                'Debe seleccionar al menos una mesa'
            )
        ms = Mesa.objects.filter(id__in=mesas_ids)
        if ms.count() != len(mesas_ids):
            raise ReglaNegocioViolada('Algunas mesas no existen')
        zonas = set(m.zona for m in ms)
        if len(zonas) > 1:
            raise ReglaNegocioViolada(
                'No puedes unir mesas de diferentes zonas'
            )
        mesas_actuales_ids = mesas_actuales_ids or []
        for m in ms:
            if m.id in mesas_actuales_ids:
                continue
            if m.estado != 'LIBRE':
                raise ReglaNegocioViolada(
                    f'La mesa {m.numero} no está disponible'
                )
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
        if inicio < self.HORA_APERTURA:
            raise ReglaNegocioViolada(
                'El horario de atención es de 07:00 a 22:00'
            )
        if fin > self.HORA_CIERRE:
            raise ReglaNegocioViolada(
                'El horario de atención es de 07:00 a 22:00'
            )
        if inicio >= fin:
            raise ReglaNegocioViolada(
                'La hora de inicio debe ser anterior a la hora de fin'
            )
        if cliente_contacto:
            if '@' in cliente_contacto:
                if not re.match(
                    r"[^@]+@[^@]+\.[^@]+", cliente_contacto
                ):
                    raise ReglaNegocioViolada(
                        'Correo electrónico inválido'
                    )
            else:
                if (not cliente_contacto.isdigit()
                        or len(cliente_contacto) != 9):
                    raise ReglaNegocioViolada(
                        'El celular debe tener 9 dígitos'
                    )
        return {
            'mesas': ms, 'num_personas': num_personas,
            'cliente_nombre': cliente_nombre,
            'cliente_contacto': cliente_contacto,
            'fecha': fecha, 'hora_inicio': hora_inicio,
            'hora_fin': hora_fin, 'observacion': observacion,
        }

    def obtener_datos_edicion(self, reserva_id: int):
        from django.db.models import Q
        reserva = Reserva.objects.select_related(
            'mesa', 'union_mesa'
        ).filter(id=reserva_id).first()
        if not reserva:
            raise RecursoNoEncontrado('Reserva no encontrada')

        mesas_actuales_ids = []
        if reserva.mesa:
            mesas_actuales_ids.append(reserva.mesa.id)
        elif reserva.union_mesa:
            mesas_actuales_ids = [m.id for m in reserva.union_mesa.mesas.all()]

        mesas = Mesa.activos.filter(
            Q(estado='LIBRE') | Q(id__in=mesas_actuales_ids)
        )
        return {
            'reserva': reserva,
            'mesas': mesas,
            'mesas_actuales_ids': mesas_actuales_ids,
        }

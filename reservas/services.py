from datetime import time as time_obj, datetime
import re
from django.db import transaction
from core.excepciones import (
    RecursoNoEncontrado, CapacidadExcedida, ReglaNegocioViolada,
)
from mesas.services import _notificar_plano
from dominio.entidades.union_mesa import UnionMesa

from dominio.puertos.repositorios import (
    IReservaRepository, IMesaRepository, IUnionMesaRepository,
)
from typing import Optional


class ReservaService:
    HORA_APERTURA = time_obj(7, 0)
    HORA_CIERRE = time_obj(22, 0)

    def __init__(self, reserva_repo: Optional[IReservaRepository] = None,
                 mesa_repo: Optional[IMesaRepository] = None,
                 union_mesa_repo: Optional[IUnionMesaRepository] = None):
        self.reserva_repo = reserva_repo
        self.mesa_repo = mesa_repo
        self.union_mesa_repo = union_mesa_repo

    def listar(self):
        return self.reserva_repo.listar()

    @transaction.atomic
    def crear(self, mesas_ids: list, fecha, hora_inicio, hora_fin,
              num_personas: int, cliente_nombre: str,
              cliente_contacto: str = '', observacion: str = '',
              usuario=None):
        datos = self._validar_datos(
            mesas_ids, fecha, hora_inicio, hora_fin,
            num_personas, cliente_nombre, cliente_contacto, observacion
        )
        ms = datos['mesas']
        mesa_obj = ms[0] if len(ms) == 1 else None
        union_mesa_obj = None
        if len(ms) > 1:
            union_mesa_obj = self.union_mesa_repo.guardar(
                UnionMesa(id=None, mesa_ids=[m.id for m in ms], activo=True)
            )

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
        reserva = self.reserva_repo.guardar(reserva_domain)
        return reserva

    @transaction.atomic
    def cancelar(self, reserva_id: int):
        reserva = self.reserva_repo.obtener_con_bloqueo(reserva_id)
        if not reserva:
            raise RecursoNoEncontrado('Reserva no encontrada')
        if not reserva.activo:
            raise ReglaNegocioViolada('Esta reserva ya estaba cancelada')

        reserva.activo = False
        self.reserva_repo.guardar(reserva)

        if reserva.mesa_id:
            tiene_otra = any(r.id != reserva.id for r in self.reserva_repo.listar_activas_por_mesa(reserva.mesa_id))
            if not tiene_otra:
                mesa = self.mesa_repo.obtener_por_id(reserva.mesa_id)
                if mesa:
                    mesa.estado = 'LIBRE'
                    self.mesa_repo.guardar(mesa)
        elif reserva.union_mesa_id:
            tiene_otra = any(r.id != reserva.id for r in self.reserva_repo.listar_activas_por_union(reserva.union_mesa_id))
            if not tiene_otra:
                union = self.union_mesa_repo.obtener_por_id(reserva.union_mesa_id)
                if union:
                    for m in self.mesa_repo.listar_activas_por_ids(union.mesa_ids):
                        m.estado = 'LIBRE'
                        self.mesa_repo.guardar(m)
                    union.activo = False
                    self.union_mesa_repo.guardar(union)

        _notificar_plano()
        return reserva

    @transaction.atomic
    def finalizar(self, reserva_id: int):
        reserva = self.reserva_repo.obtener_con_bloqueo(reserva_id)
        if not reserva:
            raise RecursoNoEncontrado('Reserva no encontrada')
        if not reserva.activo:
            raise ReglaNegocioViolada('Esta reserva ya no está activa')

        reserva.activo = False
        reserva.finalizada = True
        self.reserva_repo.guardar(reserva)

        if reserva.mesa_id:
            tiene_otra = any(r.id != reserva.id for r in self.reserva_repo.listar_activas_por_mesa(reserva.mesa_id))
            if not tiene_otra:
                mesa = self.mesa_repo.obtener_por_id(reserva.mesa_id)
                if mesa:
                    mesa.estado = 'LIMPIEZA'
                    self.mesa_repo.guardar(mesa)
        elif reserva.union_mesa_id:
            tiene_otra = any(r.id != reserva.id for r in self.reserva_repo.listar_activas_por_union(reserva.union_mesa_id))
            if not tiene_otra:
                union = self.union_mesa_repo.obtener_por_id(reserva.union_mesa_id)
                if union:
                    for m in self.mesa_repo.listar_activas_por_ids(union.mesa_ids):
                        m.estado = 'LIMPIEZA'
                        self.mesa_repo.guardar(m)
                    union.activo = False
                    self.union_mesa_repo.guardar(union)

        _notificar_plano()
        return reserva

    @transaction.atomic
    def editar(self, reserva_id: int, mesas_ids: list, fecha,
               hora_inicio, hora_fin, num_personas: int,
               cliente_nombre: str, cliente_contacto: str = '',
               observacion: str = '', usuario=None):
        reserva = self.reserva_repo.obtener_con_bloqueo(reserva_id)
        if not reserva:
            raise RecursoNoEncontrado('Reserva no encontrada')
        if not reserva.activo:
            raise ReglaNegocioViolada(
                'No puedes editar una reserva cancelada'
            )

        # Guardar las referencias anteriores por ID
        vieja_mesa_id = reserva.mesa_id
        vieja_union_id = reserva.union_mesa_id

        mesas_actuales_ids = []
        if vieja_mesa_id:
            mesas_actuales_ids.append(vieja_mesa_id)
        elif vieja_union_id:
            vieja_union = self.union_mesa_repo.obtener_por_id(vieja_union_id)
            if vieja_union:
                mesas_actuales_ids = list(vieja_union.mesa_ids)

        datos = self._validar_datos(
            mesas_ids, fecha, hora_inicio, hora_fin,
            num_personas, cliente_nombre, cliente_contacto,
            observacion, mesas_actuales_ids=mesas_actuales_ids,
        )

        ms = datos['mesas']
        ms_ids = [m.id for m in ms]
        if len(ms) == 1:
            reserva.mesa_id = ms[0].id
            reserva.union_mesa_id = None
        else:
            union_mesa_obj = self.union_mesa_repo.guardar(
                UnionMesa(id=None, mesa_ids=ms_ids, activo=True)
            )
            reserva.mesa_id = None
            reserva.union_mesa_id = union_mesa_obj.id

        reserva.cliente_nombre = datos['cliente_nombre']
        reserva.cliente_contacto = datos['cliente_contacto']
        reserva.fecha = datos['fecha']
        reserva.hora_inicio = datos['hora_inicio']
        reserva.hora_fin = datos['hora_fin']
        reserva.num_personas = datos['num_personas']
        reserva.observacion = datos['observacion']
        self.reserva_repo.guardar(reserva)

        if vieja_mesa_id and vieja_mesa_id not in ms_ids:
            vieja_mesa = self.mesa_repo.obtener_por_id(vieja_mesa_id)
            if vieja_mesa:
                vieja_mesa.estado = 'LIBRE'
                self.mesa_repo.guardar(vieja_mesa)
        if vieja_union_id and vieja_union_id != reserva.union_mesa_id:
            vieja_union = self.union_mesa_repo.obtener_por_id(vieja_union_id)
            if vieja_union:
                vieja_union.activo = False
                self.union_mesa_repo.guardar(vieja_union)
                for m in self.mesa_repo.listar_activas_por_ids(vieja_union.mesa_ids):
                    if m.id not in ms_ids:
                        m.estado = 'LIBRE'
                        self.mesa_repo.guardar(m)

        for m in ms:
            m.estado = 'RESERVADA'
            self.mesa_repo.guardar(m)

        _notificar_plano()
        return reserva

    @transaction.atomic
    def eliminar_definitivamente(self, reserva_id: int) -> None:
        reserva = self.reserva_repo.obtener_con_bloqueo(reserva_id)
        if not reserva:
            raise RecursoNoEncontrado('Reserva no encontrada')
        if reserva.activo:
            raise ReglaNegocioViolada(
                'No puedes eliminar una reserva activa. '
                'Debes cancelarla primero.'
            )
        if reserva.mesa_id:
            mesa = self.mesa_repo.obtener_por_id(reserva.mesa_id)
            if mesa and mesa.estado == 'RESERVADA':
                mesa.estado = 'LIBRE'
                self.mesa_repo.guardar(mesa)
        elif reserva.union_mesa_id:
            union = self.union_mesa_repo.obtener_por_id(reserva.union_mesa_id)
            if union:
                for m in self.mesa_repo.listar_activas_por_ids(union.mesa_ids):
                    if m.estado == 'RESERVADA':
                        m.estado = 'LIBRE'
                        self.mesa_repo.guardar(m)
                if union.activo:
                    union.activo = False
                    self.union_mesa_repo.guardar(union)
        self.reserva_repo.eliminar(reserva.id)
        _notificar_plano()

    def _validar_datos(self, mesas_ids, fecha, hora_inicio, hora_fin,
                       num_personas, cliente_nombre, cliente_contacto,
                       observacion, mesas_actuales_ids=None):
        if not mesas_ids:
            raise ReglaNegocioViolada(
                'Debe seleccionar al menos una mesa'
            )
        ms = self.mesa_repo.listar_activas_por_ids(mesas_ids)
        if len(ms) != len(mesas_ids):
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
        reserva = self.reserva_repo.obtener_por_id(reserva_id)
        if not reserva:
            raise RecursoNoEncontrado('Reserva no encontrada')

        mesas_actuales_ids = []
        if reserva.mesa_id:
            mesas_actuales_ids.append(reserva.mesa_id)
        elif reserva.union_mesa_id:
            union = self.union_mesa_repo.obtener_por_id(reserva.union_mesa_id)
            if union:
                mesas_actuales_ids = list(union.mesa_ids)

        todas = self.mesa_repo.listar_activas()
        mesas = [m for m in todas if m.estado == 'LIBRE' or m.id in mesas_actuales_ids]
        return {
            'reserva': reserva,
            'mesas': mesas,
            'mesas_actuales_ids': mesas_actuales_ids,
        }

from django.db import transaction
from core.excepciones import (
    RecursoNoEncontrado, UnionInvalida,
    CajaNoAbierta, ReglaNegocioViolada, AppError,
)
from dominio.puertos.repositorios import IMesaRepository


class MesaService:
    def __init__(self, mesa_repo: IMesaRepository):
        self.repo = mesa_repo

    @transaction.atomic
    def obtener_o_crear_comanda_activa(self, mesa_id: int, usuario):
        from pedidos.services import ComandaService
        return ComandaService.abrir(mesa_id, usuario)

    def cambiar_estado(self, mesa_id: int, nuevo_estado: str):
        mesa_domain = self.repo.obtener_por_id(mesa_id)
        if not mesa_domain:
            raise RecursoNoEncontrado('Mesa no encontrada')
        from mesas.models import Mesa
        mesa_model = Mesa.activos.get(id=mesa_id)
        mesa_model.estado = nuevo_estado
        mesa_model.save(update_fields=['estado'])
        _notificar_plano()
        return mesa_model

    def marcar_libre(self, mesa_id: int):
        from mesas.models import Mesa, UnionMesa
        mesa_domain = self.repo.obtener_por_id(mesa_id)
        if not mesa_domain:
            raise RecursoNoEncontrado('Mesa no encontrada')
        mesa_model = Mesa.activos.get(id=mesa_id)
        if mesa_model.estado != 'LIMPIEZA':
            raise ReglaNegocioViolada('Solo se puede marcar libre una mesa en limpieza')
        tiene_reserva = mesa_model.reservas.filter(activo=True).exists()
        union = UnionMesa.activos.filter(mesas=mesa_model).first()
        if union:
            tiene_reserva = tiene_reserva or union.reservas.filter(activo=True).exists()
        mesa_model.estado = 'RESERVADA' if tiene_reserva else 'LIBRE'
        mesa_model.save(update_fields=['estado'])
        _notificar_plano()
        return mesa_model

    def obtener_plano(self):
        from mesas.models import Mesa, UnionMesa
        mesas = Mesa.activos.all()
        uniones = UnionMesa.activos.prefetch_related('mesas')

        union_mesas_ids = set()
        union_labels = {}
        union_ids = {}
        processed_mesa_ids = set()
        items = []

        for union in uniones:
            miembros = list(union.mesas.all())
            nums = sorted([m.numero for m in miembros])
            label = ' + '.join([f'Mesa {x}' for x in nums])
            estados = set(m.estado for m in miembros)
            if 'OCUPADA' in estados:
                estado_resumen = 'OCUPADA'
            elif 'RESERVADA' in estados:
                estado_resumen = 'RESERVADA'
            elif 'LIMPIEZA' in estados:
                estado_resumen = 'LIMPIEZA'
            else:
                estado_resumen = 'LIBRE'
            capacidad = sum(m.capacidad for m in miembros)
            for m in miembros:
                union_mesas_ids.add(m.id)
                union_labels[m.id] = label
                union_ids[m.id] = union.id
                processed_mesa_ids.add(m.id)
            items.append({
                'type': 'union',
                'union_id': union.id,
                'mesas': miembros,
                'nums': nums,
                'label': label,
                'capacidad': capacidad,
                'estado': estado_resumen,
                'zona': miembros[0].zona,
            })

        for mesa in mesas:
            if mesa.id in processed_mesa_ids:
                continue
            items.append({
                'type': 'mesa',
                'mesa': mesa,
            })

        return {
            'items': items,
            'union_mesas_ids': union_mesas_ids,
            'union_labels': union_labels,
            'union_ids': union_ids,
        }

    def obtener_detalle(self, mesa_id: int, usuario=None):
        from mesas.models import Mesa, UnionMesa
        from pedidos.models import Comanda
        from menu.models import Categoria

        mesa = Mesa.objects.get(id=mesa_id)

        comanda = Comanda.objects.filter(
            mesa=mesa, estado__in=['ABIERTA', 'EN_PREPARACION', 'LISTA']
        ).prefetch_related('lineas__plato').first()

        if comanda and mesa.estado == 'LIBRE':
            try:
                from pedidos.services import ComandaService
                ComandaService.anular(comanda.id, usuario=usuario)
            except AppError:
                pass
            comanda = None

        union_activa = UnionMesa.activos.filter(mesas=mesa).prefetch_related('mesas').first()
        if not comanda and union_activa:
            comanda = Comanda.objects.filter(
                mesa__in=union_activa.mesas.all(),
                estado__in=['ABIERTA', 'EN_PREPARACION', 'LISTA']
            ).prefetch_related('lineas__plato').first()

        categorias = Categoria.objects.prefetch_related('platos').all()

        return {
            'mesa': mesa,
            'comanda_activa': comanda,
            'categorias': categorias,
            'union_activa': union_activa,
        }

    def eliminar(self, mesa_id: int, usuario=None) -> None:
        from mesas.models import Mesa
        mesa_domain = self.repo.obtener_por_id(mesa_id)
        if not mesa_domain:
            raise RecursoNoEncontrado('Mesa no encontrada')
        mesa_model = Mesa.activos.get(id=mesa_id)
        if mesa_model.estado != 'LIBRE':
            raise ReglaNegocioViolada('No se puede eliminar una mesa que no está libre')
        mesa_model.eliminar(usuario=usuario)


class UnionMesaService:
    def __init__(self, mesa_repo: IMesaRepository):
        self.mesa_repo = mesa_repo

    @transaction.atomic
    def crear(self, mesa_ids: list):
        from mesas.models import Mesa, UnionMesa
        from pedidos.models import Comanda

        if len(mesa_ids) < 2:
            raise UnionInvalida('Selecciona al menos 2 mesas')

        mesas = Mesa.activos.filter(id__in=mesa_ids)
        if mesas.count() < 2:
            raise UnionInvalida('Las mesas seleccionadas no existen')

        if mesas.filter(estado='RESERVADA').exists():
            raise UnionInvalida('No puedes unir mesas que están reservadas')

        zonas = set(m.zona for m in mesas)
        if len(zonas) > 1:
            raise UnionInvalida('No puedes unir mesas de diferentes zonas')

        selected_ids = set(m.id for m in mesas)
        uniones_activas = UnionMesa.activos.prefetch_related('mesas')
        for u in uniones_activas:
            union_ids_set = set(m.id for m in u.mesas.all())
            if union_ids_set == selected_ids:
                raise UnionInvalida('Ya existe una unión activa con esas mesas')

        union = UnionMesa.objects.create()
        union.mesas.set(mesas)

        comandas_activas = Comanda.objects.filter(
            mesa_id__in=mesa_ids,
            estado__in=['ABIERTA', 'EN_PREPARACION', 'LISTA']
        )
        if comandas_activas.exists():
            for m in mesas:
                if m.estado == 'LIBRE':
                    m.estado = 'OCUPADA'
                    m.save(update_fields=['estado'])
        if comandas_activas.count() >= 2:
            from pedidos.services import ComandaService
            principal = comandas_activas.first()
            for otras in comandas_activas[1:]:
                ComandaService.fusionar(principal.id, otras.id)

        _notificar_plano()
        return union

    @transaction.atomic
    def agregar_mesa(self, union_id: int, mesa_id: int, usuario):
        from mesas.models import Mesa, UnionMesa
        from pedidos.models import Comanda
        from caja.models import Caja

        union = UnionMesa.activos.filter(id=union_id).first()
        if not union:
            raise RecursoNoEncontrado('Unión no encontrada')
        mesa_domain = self.mesa_repo.obtener_por_id(mesa_id)
        if not mesa_domain:
            raise RecursoNoEncontrado('Mesa no encontrada')
        mesa_model = Mesa.activos.get(id=mesa_id)

        if union.mesas.filter(id=mesa_id).exists():
            raise UnionInvalida(f'Mesa {mesa_model.numero} ya está en la unión')
        if union.esta_reservada():
            raise UnionInvalida('La unión está reservada')
        if mesa_model.estado == 'RESERVADA':
            raise UnionInvalida('No puedes agregar una mesa reservada')

        zona_union = union.mesas.first().zona
        if mesa_model.zona != zona_union:
            raise UnionInvalida('Las mesas deben ser de la misma zona')

        union.mesas.add(mesa_model)
        comanda_union = Comanda.objects.filter(
            mesa__in=union.mesas.all(),
            estado__in=['ABIERTA', 'EN_PREPARACION', 'LISTA']
        ).exclude(mesa=mesa_model).first()

        if comanda_union:
            if not Caja.objects.filter(estado='ABIERTA').exists():
                raise CajaNoAbierta('No hay un turno de caja abierto')
            mesa_model.estado = 'OCUPADA'
            mesa_model.save(update_fields=['estado'])
            from pedidos.services import ComandaService
            comanda_nueva = ComandaService.abrir(mesa_model.id, usuario)
            ComandaService.fusionar(comanda_union.id, comanda_nueva.id)

        _notificar_plano()
        return union

    @transaction.atomic
    def deshacer(self, union_id: int, usuario) -> None:
        from mesas.models import Mesa, UnionMesa
        from pedidos.models import Comanda

        union = UnionMesa.activos.filter(id=union_id).first()
        if not union:
            raise RecursoNoEncontrado('Unión no encontrada')
        if union.esta_reservada():
            raise UnionInvalida('No puedes deshacer una unión con reserva activa')

        mesa_ids = [m.id for m in union.mesas.all()]
        comandas_activas = Comanda.objects.filter(
            mesa_id__in=mesa_ids,
            estado__in=['ABIERTA', 'EN_PREPARACION', 'LISTA']
        )
        errores = []
        from pedidos.services import ComandaService
        for comanda in comandas_activas:
            try:
                ComandaService.anular(comanda.id, usuario=usuario)
            except AppError as e:
                errores.append(str(e))

        if errores:
            raise UnionInvalida('; '.join(errores))

        for mesa in union.mesas.all():
            mesa.estado = 'LIBRE'
            mesa.save(update_fields=['estado'])
        union.activo = False
        union.save(update_fields=['activo', 'actualizado_en'])
        _notificar_plano()

def _notificar_plano():
    try:
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync as async_to_safe
        channel_layer = get_channel_layer()
        async_to_safe(channel_layer.group_send)(
            'plano', {'type': 'plano_update', 'data': {'action': 'refresh'}}
        )
    except Exception:
        pass

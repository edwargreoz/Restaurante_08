from django.db import transaction
from django.utils import timezone
from core.excepciones import (
    RecursoNoEncontrado, MesaConComandaActiva,
    CapacidadExcedida, UnionInvalida, CajaNoAbierta, ReglaNegocioViolada,
    AppError,
)
from mesas.models import Mesa, UnionMesa
from pedidos.models import Comanda
from pedidos.services import ComandaService
from caja.models import Caja


class MesaService:
    @staticmethod
    @transaction.atomic
    def obtener_o_crear_comanda_activa(mesa_id: int, usuario) -> Comanda:
        return ComandaService.abrir(mesa_id, usuario)

    @staticmethod
    def cambiar_estado(mesa_id: int, nuevo_estado: str) -> Mesa:
        mesa = Mesa.activos.filter(id=mesa_id).first()
        if not mesa:
            raise RecursoNoEncontrado('Mesa no encontrada')
        mesa.estado = nuevo_estado
        mesa.save(update_fields=['estado'])
        _notificar_plano()
        return mesa

    @staticmethod
    def marcar_libre(mesa_id: int) -> Mesa:
        mesa = Mesa.activos.filter(id=mesa_id).first()
        if not mesa:
            raise RecursoNoEncontrado('Mesa no encontrada')
        if mesa.estado != 'LIMPIEZA':
            raise ReglaNegocioViolada('Solo se puede marcar libre una mesa en limpieza')
        tiene_reserva = mesa.reservas.filter(activo=True).exists()
        union = UnionMesa.activos.filter(mesas=mesa).first()
        if union:
            tiene_reserva = tiene_reserva or union.reservas.filter(activo=True).exists()
        mesa.estado = 'RESERVADA' if tiene_reserva else 'LIBRE'
        mesa.save(update_fields=['estado'])
        _notificar_plano()
        return mesa

    @staticmethod
    def obtener_plano():
        """
        Construye el plano de mesas con estados, uniones y labels.
        Retorna un dict con 'items', 'union_mesas_ids', 'union_labels', 'union_ids'.
        """
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

    @staticmethod
    def obtener_detalle(mesa_id: int, usuario=None):
        """
        Retorna el detalle de una mesa incluyendo su comanda activa.
        Si una comanda está huérfana (mesa no en uso), la anula automáticamente.
        """
        mesa = Mesa.objects.get(id=mesa_id)

        comanda = Comanda.objects.filter(
            mesa=mesa, estado__in=['ABIERTA', 'EN_PREPARACION', 'LISTA']
        ).prefetch_related('lineas__plato').first()

        # Auto-anular comandas huérfanas (mesa libre pero tiene comanda)
        if comanda and mesa.estado == 'LIBRE':
            try:
                ComandaService.anular(comanda.id, usuario=usuario)
            except AppError:
                pass
            comanda = None

        # Buscar por unión (si esta mesa es secundaria)
        union_activa = UnionMesa.activos.filter(mesas=mesa).prefetch_related('mesas').first()
        if not comanda and union_activa:
            comanda = Comanda.objects.filter(
                mesa__in=union_activa.mesas.all(),
                estado__in=['ABIERTA', 'EN_PREPARACION', 'LISTA']
            ).prefetch_related('lineas__plato').first()

        from menu.models import Categoria
        categorias = Categoria.objects.prefetch_related('platos').all()

        return {
            'mesa': mesa,
            'comanda_activa': comanda,
            'categorias': categorias,
            'union_activa': union_activa,
        }

    @staticmethod
    def eliminar(mesa_id: int, usuario=None) -> None:
        """Soft delete de una mesa."""
        mesa = Mesa.activos.filter(id=mesa_id).first()
        if not mesa:
            raise RecursoNoEncontrado('Mesa no encontrada')
        if mesa.estado != 'LIBRE':
            raise ReglaNegocioViolada('No se puede eliminar una mesa que no está libre')
        mesa.eliminar(usuario=usuario)


class UnionMesaService:
    @staticmethod
    @transaction.atomic
    def crear(mesa_ids: list) -> UnionMesa:
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
            union_ids = set(m.id for m in u.mesas.all())
            if union_ids == selected_ids:
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
            principal = comandas_activas.first()
            for otras in comandas_activas[1:]:
               ComandaService.fusionar(principal.id,otras.id)

        _notificar_plano()
        return union

    @staticmethod
    @transaction.atomic
    def agregar_mesa(union_id: int, mesa_id: int, usuario) -> UnionMesa:
        union = UnionMesa.activos.filter(id=union_id).first()
        if not union:
            raise RecursoNoEncontrado('Unión no encontrada')
        mesa = Mesa.activos.filter(id=mesa_id).first()
        if not mesa:
            raise RecursoNoEncontrado('Mesa no encontrada')

        if union.mesas.filter(id=mesa_id).exists():
            raise UnionInvalida(f'Mesa {mesa.numero} ya está en la unión')
        if union.esta_reservada():
            raise UnionInvalida('La unión está reservada')
        if mesa.estado == 'RESERVADA':
            raise UnionInvalida('No puedes agregar una mesa reservada')

        zona_union = union.mesas.first().zona
        if mesa.zona != zona_union:
            raise UnionInvalida('Las mesas deben ser de la misma zona')

        union.mesas.add(mesa)
        comanda_union = Comanda.objects.filter(
            mesa__in=union.mesas.all(),
            estado__in=['ABIERTA', 'EN_PREPARACION', 'LISTA']
        ).exclude(mesa=mesa).first()

        if comanda_union:
            if not Caja.objects.filter(estado='ABIERTA').exists():
                raise CajaNoAbierta('No hay un turno de caja abierto')
            mesa.estado = 'OCUPADA'
            mesa.save(update_fields=['estado'])
            comanda_nueva = ComandaService.abrir(mesa.id, usuario)
            ComandaService.fusionar(comanda_union.id, comanda_nueva.id)

        _notificar_plano()
        return union

    @staticmethod
    @transaction.atomic
    def deshacer(union_id: int, usuario) -> None:
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

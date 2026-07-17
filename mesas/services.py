from django.db import transaction
from core.excepciones import (
    RecursoNoEncontrado, UnionInvalida,
    CajaNoAbierta, ReglaNegocioViolada, AppError,
)
from dominio.entidades.mesa import Mesa as MesaDomain
from dominio.puertos.repositorios import IMesaRepository


class MesaService:
    def __init__(self, mesa_repo: IMesaRepository):
        self.repo = mesa_repo

    @transaction.atomic
    def obtener_o_crear_comanda_activa(self, mesa_id: int, usuario):
        from infraestructura.container import get_container
        container = get_container()
        return container.comanda_service.abrir(mesa_id, usuario)

    @transaction.atomic
    def cambiar_estado(self, mesa_id: int, nuevo_estado: str):
        mesa_domain = self.repo.obtener_por_id(mesa_id)
        if not mesa_domain:
            raise RecursoNoEncontrado('Mesa no encontrada')
        from mesas.models import Mesa
        mesa_model = self.repo.obtener_con_bloqueo(mesa_id)
        mesa_model.estado = nuevo_estado
        self.repo.guardar(mesa_model)
        _notificar_plano()
        return mesa_model

    @transaction.atomic
    def marcar_libre(self, mesa_id: int):
        from mesas.models import Mesa, UnionMesa
        mesa_domain = self.repo.obtener_por_id(mesa_id)
        if not mesa_domain:
            raise RecursoNoEncontrado('Mesa no encontrada')
        mesa_model = self.repo.obtener_con_bloqueo(mesa_id)
        if mesa_model.estado != 'LIMPIEZA':
            raise ReglaNegocioViolada('Solo se puede marcar libre una mesa en limpieza')
        tiene_reserva = bool(get_container().reserva_service.repo.listar_activas_por_mesa(mesa_model.id))
        union = get_container().union_mesa_service.repo.obtener_activa_por_mesa(mesa_model.id)
        if union:
            tiene_reserva = tiene_reserva or bool(get_container().reserva_service.repo.listar_activas_por_union(union.id))
        mesa_model.estado = 'RESERVADA' if tiene_reserva else 'LIBRE'
        self.repo.guardar(mesa_model)
        _notificar_plano()
        return mesa_model

    def obtener_plano(self):
        from mesas.models import Mesa, UnionMesa
        mesas = self.repo.listar_activas()
        uniones = get_container().union_mesa_service.repo.listar_activas()

        union_mesas_ids = set()
        union_labels = {}
        union_ids = {}
        processed_mesa_ids = set()
        items = []

        for union in uniones:
            miembros = [m for m in get_container().mesa_service.repo.listar_activas_por_ids(union.mesas) if m.activo]
            if len(miembros) < 2:
                union.activo = False
                get_container().union_mesa_service.repo.guardar(union)
                continue
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
        
        from menu.models import Categoria

        mesa = self.repo.obtener_por_id(mesa_id)

        comanda = get_container().comanda_service.comanda_repo.obtener_activa_por_mesa(mesa.id)

        if comanda and mesa.estado == 'LIBRE':
            try:
                from infraestructura.container import get_container
                container = get_container()
                container.comanda_service.anular(comanda.id, usuario=usuario)
            except AppError:
                pass
            comanda = None

        union_activa = get_container().union_mesa_service.repo.obtener_activa_por_mesa(mesa.id)
        if not comanda and union_activa:
            comanda = get_container().comanda_service.comanda_repo.obtener_activa_por_mesa(mesa.id)

        categorias = get_container().categoria_service.categoria_repo.listar_con_platos()

        return {
            'mesa': mesa,
            'comanda_activa': comanda,
            'categorias': categorias,
            'union_activa': union_activa,
        }

    @transaction.atomic
    def eliminar(self, mesa_id: int, usuario=None) -> None:
        from mesas.models import Mesa, UnionMesa
        mesa_domain = self.repo.obtener_por_id(mesa_id)
        if not mesa_domain:
            raise RecursoNoEncontrado('Mesa no encontrada')
        mesa_model = self.repo.obtener_con_bloqueo(mesa_id)
        if mesa_model.estado != 'LIBRE':
            raise ReglaNegocioViolada('No se puede eliminar una mesa que no está libre')
        mesa_model.eliminar(usuario=usuario)
        uniones = [get_container().union_mesa_service.repo.obtener_activa_por_mesa(mesa_model.id)]
        for union in uniones:
            mesas_activas = [m for m in get_container().mesa_service.repo.listar_activas_por_ids(union.mesas) if m.activo]
            if mesas_activas.count() < 2:
                union.activo = False
                get_container().union_mesa_service.repo.guardar(union)

    def validar_editable(self, mesa_id: int):
        mesa = self.repo.obtener_por_id(mesa_id)
        if not mesa:
            raise RecursoNoEncontrado('Mesa no encontrada')
        if mesa.estado == 'RESERVADA':
            raise ReglaNegocioViolada(
                'No puedes editar una mesa que actualmente se encuentra RESERVADA.'
            )
        return mesa

    def obtener_modelo(self, mesa_id: int):
        from mesas.models import Mesa
        return self.repo.obtener_por_id(mesa_id)

    def crear(self, numero: int, capacidad: int, zona: str, estado: str):
        mesa = MesaDomain(id=None, numero=numero, capacidad=capacidad,
                          zona=zona, estado=estado)
        return self.repo.guardar(mesa)

    def editar(self, mesa_id: int, numero: int, capacidad: int,
               zona: str, estado: str):
        mesa = self.repo.obtener_por_id(mesa_id)
        if not mesa:
            raise RecursoNoEncontrado('Mesa no encontrada')
        mesa.numero = numero
        mesa.capacidad = capacidad
        mesa.zona = zona
        mesa.estado = estado
        return self.repo.guardar(mesa)


class UnionMesaService:

    def listar(self):
        from mesas.models import UnionMesa
        return Unionself.repo.listar_activas()

    def __init__(self, mesa_repo: IMesaRepository):
        self.mesa_repo = mesa_repo

    def limpiar_uniones_invalidas(self):
        from mesas.models import Mesa, UnionMesa
        uniones = get_container().union_mesa_service.repo.listar_activas()
        desactivadas = []
        for u in uniones:
            activos = [m for m in get_container().mesa_service.repo.listar_activas_por_ids(u.mesas) if m.activo]
            if len(activos) < 2:
                u.activo = False
                get_container().union_mesa_service.repo.guardar(u)
                desactivadas.append(u)
        return uniones.exclude(id__in=[u.id for u in desactivadas])

    def obtener_datos_para_union(self):
        from mesas.models import Mesa, UnionMesa
        mesas = self.repo.listar_activas()
        uniones = self.limpiar_uniones_invalidas()
        union_mesas_ids = set()
        for u in uniones:
            for m in get_container().mesa_service.repo.listar_activas_por_ids(u.mesas):
                union_mesas_ids.add(m.id)
        mesas_disponibles = mesas.exclude(
            id__in=union_mesas_ids
        ).exclude(estado='RESERVADA')
        return {
            'mesas': mesas,
            'uniones': uniones,
            'union_mesas_ids': union_mesas_ids,
            'mesas_disponibles': mesas_disponibles,
        }

    @transaction.atomic
    def crear(self, mesa_ids: list):
        

        if len(mesa_ids) < 2:
            raise UnionInvalida('Selecciona al menos 2 mesas')

        mesas = self.repo.listar_activas_por_ids(mesa_ids)
        if mesas.count() < 2:
            raise UnionInvalida('Las mesas seleccionadas no existen')

        if mesas.filter(estado='RESERVADA').exists():
            raise UnionInvalida('No puedes unir mesas que están reservadas')

        zonas = set(m.zona for m in mesas)
        if len(zonas) > 1:
            raise UnionInvalida('No puedes unir mesas de diferentes zonas')

        selected_ids = set(m.id for m in mesas)
        uniones_activas = get_container().union_mesa_service.repo.listar_activas()
        for u in uniones_activas:
            union_ids_set = set(m.id for m in get_container().mesa_service.repo.listar_activas_por_ids(u.mesas))
            if union_ids_set == selected_ids:
                raise UnionInvalida('Ya existe una unión activa con esas mesas')

        union = get_container().union_mesa_service.repo.guardar(UnionMesa())
        union.mesas = [m.id for m in mesas]

        todas_comandas = get_container().comanda_service.comanda_repo.listar()
        comandas_activas = [c for c in todas_comandas if c.mesa_id in mesa_ids and c.estado in ['ABIERTA', 'EN_PREPARACION', 'LISTA']]
        if comandas_activas:
            for m in mesas:
                if m.estado == 'LIBRE':
                    m.estado = 'OCUPADA'
                    self.mesa_repo.guardar(m) if hasattr(self, "mesa_repo") else get_container().mesa_service.repo.guardar(m)
        if len(comandas_activas) >= 2:
            from infraestructura.container import get_container
            container = get_container()
            principal = comandas_activas.first()
            for otras in comandas_activas[1:]:
                container.comanda_service.fusionar(principal.id, otras.id)

        _notificar_plano()
        return union

    @transaction.atomic
    def agregar_mesa(self, union_id: int, mesa_id: int, usuario):
        
        from caja.models import Caja

        union = get_container().union_mesa_service.repo.obtener_por_id(union_id)
        if not union:
            raise RecursoNoEncontrado('Unión no encontrada')
        mesa_domain = self.mesa_repo.obtener_por_id(mesa_id)
        if not mesa_domain:
            raise RecursoNoEncontrado('Mesa no encontrada')
        mesa_model = self.repo.obtener_por_id(mesa_id)

        if mesa_id in union.mesas:
            raise UnionInvalida(f'Mesa {mesa_model.numero} ya está en la unión')
        if union.esta_reservada():
            raise UnionInvalida('La unión está reservada')
        if mesa_model.estado == 'RESERVADA':
            raise UnionInvalida('No puedes agregar una mesa reservada')

        zona_union = get_container().mesa_service.repo.obtener_por_id(union.mesas[0]).zona if union.mesas else ''
        if mesa_model.zona != zona_union:
            raise UnionInvalida('Las mesas deben ser de la misma zona')

        union.mesas.append(mesa_model.id)
        todas_comandas = get_container().comanda_service.comanda_repo.listar()
        comandas_activas_union = [c for c in todas_comandas if c.mesa_id in union.mesas and c.estado in ['ABIERTA', 'EN_PREPARACION', 'LISTA'] and c.mesa_id != mesa_model.id]
        comanda_union = comandas_activas_union[0] if comandas_activas_union else None

        if comanda_union:
            if not get_container().caja_service.repo.obtener_abierta() is not None:
                raise CajaNoAbierta('No hay un turno de caja abierto')
            mesa_model.estado = 'OCUPADA'
            self.repo.guardar(mesa_model)
            from infraestructura.container import get_container
            container = get_container()
            comanda_nueva = container.comanda_service.abrir(mesa_model.id, usuario)
            container.comanda_service.fusionar(comanda_union.id, comanda_nueva.id)

        _notificar_plano()
        return union

    @transaction.atomic
    def deshacer(self, union_id: int, usuario) -> None:
        

        union = get_container().union_mesa_service.repo.obtener_por_id(union_id)
        if not union:
            raise RecursoNoEncontrado('Unión no encontrada')
        if union.esta_reservada():
            raise UnionInvalida('No puedes deshacer una unión con reserva activa')

        mesa_ids = [m.id for m in get_container().mesa_service.repo.listar_activas_por_ids(union.mesas)]
        todas_comandas = get_container().comanda_service.comanda_repo.listar()
        comandas_activas = [c for c in todas_comandas if c.mesa_id in mesa_ids and c.estado in ['ABIERTA', 'EN_PREPARACION', 'LISTA']]
        errores = []
        from infraestructura.container import get_container
        container = get_container()
        for comanda in comandas_activas:
            try:
                container.comanda_service.anular(comanda.id, usuario=usuario)
            except AppError as e:
                errores.append(str(e))

        if errores:
            raise UnionInvalida('; '.join(errores))

        for mesa in get_container().mesa_service.repo.listar_activas_por_ids(union.mesas):
            mesa.estado = 'LIBRE'
            get_container().mesa_service.repo.guardar(mesa)
        union.activo = False
        get_container().union_mesa_service.repo.guardar(union)
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

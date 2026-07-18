from core.excepciones import (
    RecursoNoEncontrado, UnionInvalida,
    CajaNoAbierta, ReglaNegocioViolada, AppError,
)
from dominio.entidades.mesa import Mesa as MesaDomain
from dominio.entidades.union_mesa import UnionMesa
from dominio.puertos.repositorios import (
    IMesaRepository, IComandaRepository,
    IReservaRepository, IUnionMesaRepository,
)
from dominio.puertos.notificador import INotificadorPlano


class MesaService:
    def __init__(self, mesa_repo: IMesaRepository,
                 comanda_repo: IComandaRepository = None,
                 reserva_repo: IReservaRepository = None,
                 union_mesa_repo: IUnionMesaRepository = None,
                 notificador_plano: INotificadorPlano = None):
        self.repo = mesa_repo
        self.comanda_repo = comanda_repo
        self.reserva_repo = reserva_repo
        self.union_mesa_repo = union_mesa_repo
        self.notificador_plano = notificador_plano

    def listar_activas(self):
        return self.repo.listar_activas()

    def obtener_por_id(self, mesa_id: int):
        return self.repo.obtener_por_id(mesa_id)

    def obtener_o_crear_comanda_activa(self, mesa_id: int, usuario,
                                       comanda_service=None):
        return comanda_service.abrir(mesa_id, usuario)

    def cambiar_estado(self, mesa_id: int, nuevo_estado: str):
        mesa_domain = self.repo.obtener_por_id(mesa_id)
        if not mesa_domain:
            raise RecursoNoEncontrado('Mesa no encontrada')
        mesa_model = self.repo.obtener_con_bloqueo(mesa_id)
        mesa_model.estado = nuevo_estado
        self.repo.guardar(mesa_model)
        if self.notificador_plano:
            self.notificador_plano.notificar_refresh()
        return mesa_model

    def marcar_libre(self, mesa_id: int):
        mesa_domain = self.repo.obtener_por_id(mesa_id)
        if not mesa_domain:
            raise RecursoNoEncontrado('Mesa no encontrada')
        mesa_model = self.repo.obtener_con_bloqueo(mesa_id)
        if mesa_model.estado != 'LIMPIEZA':
            raise ReglaNegocioViolada('Solo se puede marcar libre una mesa en limpieza')
        tiene_reserva = bool(self.reserva_repo.listar_activas_por_mesa(mesa_model.id))
        union = self.union_mesa_repo.obtener_activa_por_mesa(mesa_model.id)
        if union:
            tiene_reserva = tiene_reserva or bool(self.reserva_repo.listar_activas_por_union(union.id))
        mesa_model.estado = 'RESERVADA' if tiene_reserva else 'LIBRE'
        self.repo.guardar(mesa_model)
        if self.notificador_plano:
            self.notificador_plano.notificar_refresh()
        return mesa_model

    def obtener_plano(self):
        mesas = self.repo.listar_activas()
        uniones = self.union_mesa_repo.listar_activas()

        union_mesas_ids = set()
        union_labels = {}
        union_ids = {}
        processed_mesa_ids = set()
        items = []

        for union in uniones:
            miembros = [m for m in self.repo.listar_activas_por_ids(union.mesa_ids) if m.activo]
            if len(miembros) < 2:
                union.activo = False
                self.union_mesa_repo.guardar(union)
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

    def obtener_detalle(self, mesa_id: int, usuario=None,
                        comanda_service=None, categoria_service=None):
        mesa = self.repo.obtener_por_id(mesa_id)

        comandas_mesa = self.comanda_repo.listar_por_mesa(mesa.id)
        comanda = next((c for c in comandas_mesa if c.estado in ['ABIERTA', 'EN_PREPARACION', 'LISTA']), None)

        if comanda and mesa.estado == 'LIBRE':
            try:
                comanda_service.anular(comanda.id, usuario=usuario)
            except AppError:
                pass
            comanda = None

        union_activa = self.union_mesa_repo.obtener_activa_por_mesa(mesa.id)
        if not comanda and union_activa:
            comandas_mesa2 = self.comanda_repo.listar_por_mesa(mesa.id)
            comanda = next((c for c in comandas_mesa2 if c.estado in ['ABIERTA', 'EN_PREPARACION', 'LISTA']), None)

        categorias = categoria_service.listar_con_platos()

        return {
            'mesa': mesa,
            'comanda_activa': comanda,
            'categorias': categorias,
            'union_activa': union_activa,
        }

    def eliminar(self, mesa_id: int, usuario=None) -> None:
        mesa_domain = self.repo.obtener_por_id(mesa_id)
        if not mesa_domain:
            raise RecursoNoEncontrado('Mesa no encontrada')
        mesa_model = self.repo.obtener_con_bloqueo(mesa_id)
        if mesa_model.estado != 'LIBRE':
            raise ReglaNegocioViolada('No se puede eliminar una mesa que no está libre')
        # Soft delete: marcar como inactiva
        mesa_model.activo = False
        self.repo.guardar(mesa_model)
        union = self.union_mesa_repo.obtener_activa_por_mesa(mesa_model.id)
        if union:
            mesas_activas = [m for m in self.repo.listar_activas_por_ids(union.mesa_ids) if m.activo]
            if len(mesas_activas) < 2:
                union.activo = False
                self.union_mesa_repo.guardar(union)

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
        return self.obtener_por_id(mesa_id)

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
        return self.repo.listar_activas()

    def __init__(self, mesa_repo: IMesaRepository,
                 comanda_repo: IComandaRepository = None,
                 union_mesa_repo: IUnionMesaRepository = None,
                 caja_repo=None,
                 notificador_plano: INotificadorPlano = None):
        self.mesa_repo = mesa_repo
        self.comanda_repo = comanda_repo
        self.repo = union_mesa_repo
        self.caja_repo = caja_repo
        self.notificador_plano = notificador_plano

    def limpiar_uniones_invalidas(self):
        uniones = self.repo.listar_activas()
        desactivadas = []
        for u in uniones:
            activos = [m for m in self.mesa_repo.listar_activas_por_ids(u.mesa_ids) if m.activo]
            if len(activos) < 2:
                u.activo = False
                self.repo.guardar(u)
                desactivadas.append(u)
        desactivadas_ids = {u.id for u in desactivadas}
        return [u for u in uniones if u.id not in desactivadas_ids]

    def obtener_datos_para_union(self):
        mesas = self.mesa_repo.listar_activas()
        uniones = self.limpiar_uniones_invalidas()
        union_mesas_ids = set()
        for u in uniones:
            for m in self.mesa_repo.listar_activas_por_ids(u.mesa_ids):
                union_mesas_ids.add(m.id)
        mesas_disponibles = [m for m in mesas if m.id not in union_mesas_ids and m.estado != 'RESERVADA']
        return {
            'mesas': mesas,
            'uniones': uniones,
            'union_mesas_ids': union_mesas_ids,
            'mesas_disponibles': mesas_disponibles,
        }

    def crear(self, mesa_ids: list, comanda_service=None):
        if len(mesa_ids) < 2:
            raise UnionInvalida('Selecciona al menos 2 mesas')

        mesas = self.mesa_repo.listar_activas_por_ids(mesa_ids)
        if len(mesas) < 2:
            raise UnionInvalida('Las mesas seleccionadas no existen')

        if any(m.estado == 'RESERVADA' for m in mesas):
            raise UnionInvalida('No puedes unir mesas que están reservadas')

        zonas = set(m.zona for m in mesas)
        if len(zonas) > 1:
            raise UnionInvalida('No puedes unir mesas de diferentes zonas')

        selected_ids = set(m.id for m in mesas)
        uniones_activas = self.repo.listar_activas()
        for u in uniones_activas:
            if set(u.mesa_ids) == selected_ids:
                raise UnionInvalida('Ya existe una unión activa con esas mesas')

        union = self.repo.guardar(UnionMesa(id=None, mesa_ids=[m.id for m in mesas], activo=True))

        todas_comandas = self.comanda_repo.listar()
        comandas_activas = [c for c in todas_comandas if c.mesa_id in mesa_ids and c.estado in ['ABIERTA', 'EN_PREPARACION', 'LISTA']]
        if comandas_activas:
            for m in mesas:
                if m.estado == 'LIBRE':
                    m.estado = 'OCUPADA'
                    self.mesa_repo.guardar(m)
        if len(comandas_activas) >= 2:
            principal = comandas_activas[0]
            for otras in comandas_activas[1:]:
                comanda_service.fusionar(principal.id, otras.id)

        if self.notificador_plano:
            self.notificador_plano.notificar_refresh()
        return union

    def agregar_mesa(self, union_id: int, mesa_id: int, usuario,
                     comanda_service=None, caja_service=None):
        union = self.repo.obtener_por_id(union_id)
        if not union:
            raise RecursoNoEncontrado('Unión no encontrada')
        mesa_model = self.mesa_repo.obtener_por_id(mesa_id)
        if not mesa_model:
            raise RecursoNoEncontrado('Mesa no encontrada')

        if mesa_id in union.mesa_ids:
            raise UnionInvalida(f'Mesa {mesa_model.numero} ya está en la unión')
        if mesa_model.estado == 'RESERVADA':
            raise UnionInvalida('No puedes agregar una mesa reservada')

        zona_union = self.mesa_repo.obtener_por_id(union.mesa_ids[0]).zona if union.mesa_ids else ''
        if mesa_model.zona != zona_union:
            raise UnionInvalida('Las mesas deben ser de la misma zona')

        union.mesa_ids.append(mesa_model.id)
        self.repo.guardar(union)
        todas_comandas = self.comanda_repo.listar()
        comandas_activas_union = [c for c in todas_comandas if c.mesa_id in union.mesa_ids and c.estado in ['ABIERTA', 'EN_PREPARACION', 'LISTA'] and c.mesa_id != mesa_model.id]
        comanda_union = comandas_activas_union[0] if comandas_activas_union else None

        if comanda_union:
            if self.caja_repo and not self.caja_repo.obtener_abierta() is not None:
                raise CajaNoAbierta('No hay un turno de caja abierto')
            mesa_model.estado = 'OCUPADA'
            self.mesa_repo.guardar(mesa_model)
            comanda_nueva = comanda_service.abrir(mesa_model.id, usuario)
            comanda_service.fusionar(comanda_union.id, comanda_nueva.id)

        if self.notificador_plano:
            self.notificador_plano.notificar_refresh()
        return union

    def deshacer(self, union_id: int, usuario, comanda_service=None) -> None:
        union = self.repo.obtener_por_id(union_id)
        if not union:
            raise RecursoNoEncontrado('Unión no encontrada')

        mesa_ids = union.mesa_ids
        todas_comandas = self.comanda_repo.listar()
        comandas_activas = [c for c in todas_comandas if c.mesa_id in mesa_ids and c.estado in ['ABIERTA', 'EN_PREPARACION', 'LISTA']]
        errores = []
        for comanda in comandas_activas:
            try:
                comanda_service.anular(comanda.id, usuario=usuario)
            except AppError as e:
                errores.append(str(e))

        if errores:
            raise UnionInvalida('; '.join(errores))

        for mesa in self.mesa_repo.listar_activas_por_ids(union.mesa_ids):
            mesa.estado = 'LIBRE'
            self.mesa_repo.guardar(mesa)
        union.activo = False
        self.repo.guardar(union)
        if self.notificador_plano:
            self.notificador_plano.notificar_refresh()

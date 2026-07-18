from decimal import Decimal
from dominio.entidades.insumo import Insumo as InsumoDomain
from dominio.entidades.movimiento_insumo import MovimientoInsumo
from dominio.entidades.unidad_conversion import UnidadConversion as UnidadConversionDomain
from dominio.puertos.repositorios import (
    IInsumoRepository, IUnidadConversionRepository,
    IMovimientoInsumoRepository,
)
from core.excepciones import (
    RecursoNoEncontrado, ReglaNegocioViolada,
)
from dominio.entidades.unidad_conversion import convertir_unidad


class InsumoService:

    def obtener_queryset_api(self):
        return self.repo.listar()

    def __init__(self, insumo_repo: IInsumoRepository,
                 unidad_conversion_repo: IUnidadConversionRepository = None,
                 movimiento_insumo_repo: IMovimientoInsumoRepository = None):
        self.repo = insumo_repo
        self.unidad_conversion_repo = unidad_conversion_repo
        self.movimiento_insumo_repo = movimiento_insumo_repo

    def listar_insumos(self):
        return self.repo.listar()

    def obtener_por_id(self, insumo_id: int):
        insumo_domain = self.repo.obtener_por_id(insumo_id)
        if not insumo_domain:
            raise RecursoNoEncontrado('Insumo no encontrado')
        return insumo_domain

    def obtener_por_nombre(self, nombre: str):
        insumos = self.repo.listar()
        return next((i for i in insumos if i.nombre.lower() == nombre.lower()), None)

    def crear(self, nombre: str, unidad: str,
              stock_actual=Decimal('0'), stock_minimo=Decimal('0'),
              costo_unitario=Decimal('0')):
        insumo_domain = InsumoDomain(
            id=None, nombre=nombre, unidad=unidad,
            stock_actual=stock_actual, stock_minimo=stock_minimo,
            costo_unitario=costo_unitario,
        )
        self.repo.guardar(insumo_domain)
        return next((i for i in self.repo.listar() if i.nombre == nombre), None)

    def actualizar(self, insumo_id: int, **kwargs):
        insumo_domain = self.repo.obtener_por_id(insumo_id)
        if not insumo_domain:
            raise RecursoNoEncontrado('Insumo no encontrado')
        for attr, value in kwargs.items():
            setattr(insumo_domain, attr, value)
        self.repo.guardar(insumo_domain)
        return insumo_domain

    def eliminar(self, insumo_id: int):
        insumo_domain = self.repo.obtener_por_id(insumo_id)
        if not insumo_domain:
            raise RecursoNoEncontrado('Insumo no encontrado')
        self.repo.eliminar(insumo_id)

    def registrar_compra(self, insumo_id: int, unidad_conversion_id: int,
                         cantidad_unidades: int, costo_total: Decimal,
                         usuario=None):
        insumo = self.repo.obtener_por_id(insumo_id)
        if not insumo:
            raise RecursoNoEncontrado('Insumo no encontrado')
        uc = self.unidad_conversion_repo.obtener_por_id(unidad_conversion_id)
        if not uc:
            raise RecursoNoEncontrado("Unidad de conversion no encontrada")
        cantidad_base = uc.factor_conversion * cantidad_unidades
        stock_anterior = insumo.stock_actual
        insumo.stock_actual += cantidad_base
        costo_unitario = (
            costo_total / cantidad_base if cantidad_base > 0 else Decimal('0')
        )
        insumo.costo_unitario = costo_unitario
        self.repo.guardar(insumo)
        return self.movimiento_insumo_repo.guardar(MovimientoInsumo(
            insumo_id=insumo.id, tipo='COMPRA',
            cantidad=cantidad_base,
            stock_anterior=stock_anterior,
            stock_posterior=insumo.stock_actual,
            usuario_id=getattr(usuario, 'id', None),
            observacion=f'Compra: {cantidad_unidades} {uc.nombre}',
            origen='COMPRA',
        ))

    def ajustar_stock(self, insumo_id: int, nueva_cantidad: Decimal,
                      motivo: str, usuario=None):
        insumo = self.repo.obtener_por_id(insumo_id)
        if not insumo:
            raise RecursoNoEncontrado('Insumo no encontrado')
        stock_anterior = insumo.stock_actual
        diferencia = nueva_cantidad - stock_anterior
        insumo.stock_actual = nueva_cantidad
        self.repo.guardar(insumo)
        return self.movimiento_insumo_repo.guardar(MovimientoInsumo(
            insumo_id=insumo.id, tipo='AJUSTE',
            cantidad=abs(diferencia),
            stock_anterior=stock_anterior,
            stock_posterior=insumo.stock_actual,
            usuario_id=getattr(usuario, 'id', None),
            observacion=motivo,
            origen='AJUSTE',
        ))
    
class RecetaService:

    def listar_receta_insumos(self):
        return self.repo.listar_receta_insumos()


    def obtener_queryset_api(self):
        return self.repo.listar()

    def __init__(self, receta_repo, insumo_repo: IInsumoRepository = None):
        self.repo = receta_repo
        self.insumo_repo = insumo_repo

    def listar_recetas(self):
        return self.repo.listar()

    def obtener_por_id(self, receta_id: int):
        receta = next((r for r in self.repo.listar() if r.id == receta_id), None)
        if not receta:
            raise RecursoNoEncontrado('Receta no encontrada')
        return receta

    def crear(self, nombre: str, insumos_data: list = None):
        receta = self.repo.obtener_o_crear(nombre=nombre)
        todos_ri = self.repo.listar_receta_insumos()
        es_nueva = not any(ri.receta_id == receta.id for ri in todos_ri)
        if insumos_data and es_nueva:
            for item in insumos_data:
                self.repo.obtener_receta_insumo_o_crear(
                    receta_id=receta.id,
                    insumo_id=item['insumo_id'],
                    cantidad_por_porcion=item['cantidad'],
                    unidad=item.get('unidad', 'UNIDAD'),
                    unidad_cocina_id=item.get('unidad_cocina_id'),
                )
        return receta

    def actualizar(self, receta_id: int, nombre: str = None,
                   insumos_data: list = None):
        receta = self.obtener_por_id(receta_id)
        if nombre:
            receta.nombre = nombre
            self.repo.guardar(receta)
        if insumos_data:
            # Desactivar insumos actuales de esta receta
            for ri in self.repo.listar_receta_insumos():
                if ri.receta_id == receta_id:
                    self.repo.actualizar_receta_insumo(ri.id, activo=False)
            # Crear o actualizar los nuevos
            for item in insumos_data:
                self.repo.obtener_receta_insumo_o_crear(
                    receta_id=receta.id,
                    insumo_id=item['insumo_id'],
                    cantidad_por_porcion=item['cantidad'],
                    unidad=item.get('unidad', 'UNIDAD'),
                    unidad_cocina_id=item.get('unidad_cocina_id'),
                )
        return receta

    def eliminar_insumo(self, receta_insumo_id: int):
        ri = self.repo.obtener_receta_insumo(receta_insumo_id)
        if not ri:
            raise RecursoNoEncontrado('Insumo de receta no encontrado')
        self.repo.eliminar_receta_insumo(receta_insumo_id)

    def eliminar(self, receta_id: int):
        receta = self.obtener_por_id(receta_id)
        self.repo.eliminar(receta_id)

    def calcular_insumos_para_platos(self, receta_id: int,
                                     cantidad_platos: int) -> dict:
        receta = next((r for r in self.repo.listar() if r.id == receta_id), None)
        if not receta:
            raise RecursoNoEncontrado('Receta no encontrada')
        resultado = {'insumos': [], 'disponible': True, 'faltantes': []}
        # Obtener los RecetaInsumo de esta receta
        todos_ri = self.repo.listar_receta_insumos()
        recetas_de_esta = [ri for ri in todos_ri if ri.receta_id == receta.id and ri.activo]
        for ri in recetas_de_esta:
            insumo = self.insumo_repo.obtener_por_id(ri.insumo_id)
            if not insumo:
                continue
            necesario = (
                ri.cantidad_por_porcion * Decimal(str(cantidad_platos))
            )
            necesario_base = convertir_unidad(
                necesario, ri.unidad, insumo.unidad
            )
            insumo_data = {
                'id': ri.insumo_id,
                'nombre': insumo.nombre,
                'unidad': insumo.unidad,
                'necesario': necesario_base,
                'stock_actual': insumo.stock_actual,
                'suficiente': insumo.stock_actual >= necesario_base,
            }
            resultado['insumos'].append(insumo_data)
            if not insumo_data['suficiente']:
                resultado['disponible'] = False
                resultado['faltantes'].append(insumo_data)
        return resultado

    def verificar_stock_para_plato(self, plato, cantidad: int = 1) -> bool:
        if not plato.receta_id:
            return True
        return self.calcular_insumos_para_platos(
            plato.receta_id, cantidad
        )['disponible']


class UnidadConversionService:
    """Servicio para gestionar la jerarquía de unidades de compra."""

    def __init__(self, unidad_conversion_repo: IUnidadConversionRepository):
        self.repo = unidad_conversion_repo

    def convertir(self, unidad_origen_id: int, cantidad: Decimal,
                  unidad_destino_id: int = None) -> Decimal:
        """Convierte cantidad desde unidad_origen hasta unidad_destino
        (o hasta la unidad base si no se especifica)."""
        uo = self.repo.obtener_por_id(unidad_origen_id)
        return self._convertir_recursivo(uo, cantidad, unidad_destino_id)

    def _convertir_recursivo(self, unidad, cantidad: Decimal,
                              destino_id: int = None) -> Decimal:
        if getattr(unidad, 'es_base', False):
            return cantidad
        if destino_id and unidad.id == destino_id:
            return cantidad
        total_en_sub = cantidad * unidad.factor_conversion
        parent = None
        if unidad.unidad_base_id:
            parent = self.repo.obtener_por_id(unidad.unidad_base_id)
        if not parent:
            return total_en_sub
        return self._convertir_recursivo(
            parent, total_en_sub, destino_id
        )

    def crear_cadena(self, insumo_id: int, niveles: list) -> list:
        """Crea una cadena de unidades de conversión de abajo hacia arriba.
        niveles = [
            {'nombre': 'Paquete', 'contiene': 10, 'sub_unidad': 'Subpaquete'},
            {'nombre': 'Subpaquete', 'contiene': 500, 'sub_unidad': 'Gramo'},
        ]
        La última sub_unidad debe ser una unidad base existente.
        """
        todas_unidades = self.repo.listar()
        niveles_procesados = []
        for nivel in reversed(niveles):
            sub = next((u for u in todas_unidades if getattr(u, 'nombre', '') == nivel['sub_unidad']), None)

            uc_domain = UnidadConversionDomain(
                id=None,
                nombre=nivel['nombre'],
                abreviatura=nivel.get('abreviatura', ''),
                factor_conversion=nivel['contiene'],
                unidad_base_id=sub.id if sub else None,
            )
            uc = self.repo.guardar(uc_domain)
            niveles_procesados.append(uc)
            todas_unidades.append(uc)  # Para que niveles posteriores lo encuentren
        return list(reversed(niveles_procesados))


class PresentacionInsumoService:

    def __init__(self, presentacion_repo, insumo_repo,
                 movimiento_insumo_repo=None):
        self.repo = presentacion_repo
        self.insumo_repo = insumo_repo
        self.movimiento_insumo_repo = movimiento_insumo_repo

    def listar_por_insumo(self, insumo_id: int):
        return self.repo.listar_por_insumo(insumo_id)

    def listar_catalogo(self):
        return self.repo.listar_catalogo()

    def vincular_a_insumo(self, presentacion_id: int, insumo_id: int):
        p = self.repo.obtener_por_id(presentacion_id)
        if not p:
            raise RecursoNoEncontrado('Presentación no encontrada')
        insumo = self.insumo_repo.obtener_por_id(insumo_id)
        if not insumo:
            raise RecursoNoEncontrado('Insumo no encontrado')
        from dominio.entidades.presentacion_insumo import unidades_compatibles
        if not unidades_compatibles(p.unidad_medida, insumo.unidad):
            raise ReglaNegocioViolada(
                f'La presentación "{p.nombre}" ({p.unidad_medida}) '
                f'no es compatible con el insumo ({insumo.unidad}).'
            )
        p.insumo_id = insumo_id
        return self.repo.guardar(p)

    def obtener_por_id(self, presentacion_id: int):
        p = self.repo.obtener_por_id(presentacion_id)
        if not p:
            raise RecursoNoEncontrado('Presentación no encontrada')
        return p

    def crear(self, insumo_id: int, nombre: str, cantidad,
              unidad_medida: str, costo_compra=Decimal('0'),
              es_principal=False):
        from dominio.entidades.presentacion_insumo import (
            PresentacionInsumo, unidades_compatibles,
        )
        if insumo_id:
            insumo = self.insumo_repo.obtener_por_id(insumo_id)
            if not insumo:
                raise RecursoNoEncontrado('Insumo no encontrado')
            if not unidades_compatibles(unidad_medida, insumo.unidad):
                raise ReglaNegocioViolada(
                    f'La unidad "{unidad_medida}" no es compatible con '
                    f'la unidad del insumo "{insumo.unidad}". '
                    f'Use unidades de la misma familia '
                    f'(peso: KG/GR, volumen: LT/ML, cantidad: UNIDAD).'
                )
        p = PresentacionInsumo(
            id=None, insumo_id=insumo_id, nombre=nombre,
            cantidad=Decimal(str(cantidad)), unidad_medida=unidad_medida,
            costo_compra=Decimal(str(costo_compra)), es_principal=es_principal,
        )
        return self.repo.guardar(p)

    def eliminar(self, presentacion_id: int):
        p = self.repo.obtener_por_id(presentacion_id)
        if not p:
            raise RecursoNoEncontrado('Presentación no encontrada')
        self.repo.eliminar(presentacion_id)

    def registrar_compra(self, presentacion_id: int,
                         cantidad_paquetes: int, costo_total: Decimal,
                         usuario=None):
        from dominio.entidades.presentacion_insumo import unidades_compatibles
        p = self.repo.obtener_por_id(presentacion_id)
        if not p:
            raise RecursoNoEncontrado('Presentación no encontrada')
        insumo = self.insumo_repo.obtener_por_id(p.insumo_id)
        if not insumo:
            raise RecursoNoEncontrado('Insumo no encontrado')
        if not unidades_compatibles(p.unidad_medida, insumo.unidad):
            raise ReglaNegocioViolada(
                f'La presentación "{p.nombre}" ({p.unidad_medida}) '
                f'no es compatible con el insumo ({insumo.unidad}).'
            )
        stock_anterior = insumo.stock_actual
        cantidad_base = p.calcular_stock_base(cantidad_paquetes)
        costo_total = Decimal(str(costo_total))
        stock_anterior_costo = insumo.stock_actual
        stock_anterior_costo_total = stock_anterior_costo * insumo.costo_unitario
        insumo.stock_actual += cantidad_base
        nuevo_total_valor = stock_anterior_costo_total + costo_total
        if insumo.stock_actual > 0:
            insumo.costo_unitario = nuevo_total_valor / insumo.stock_actual
        self.insumo_repo.guardar(insumo)
        if self.movimiento_insumo_repo:
            from dominio.entidades.movimiento_insumo import MovimientoInsumo
            self.movimiento_insumo_repo.guardar(MovimientoInsumo(
                insumo_id=insumo.id, tipo='COMPRA',
                cantidad=cantidad_base,
                stock_anterior=stock_anterior,
                stock_posterior=insumo.stock_actual,
                usuario_id=getattr(usuario, 'id', None),
                observacion=f'Compra: {cantidad_paquetes} x {p.nombre}',
                origen='COMPRA',
            ))
        return insumo


class UnidadCocinaService:

    def __init__(self, unidad_cocina_repo):
        self.repo = unidad_cocina_repo

    def listar(self):
        return self.repo.listar()

    def obtener_por_id(self, unidad_id: int):
        u = self.repo.obtener_por_id(unidad_id)
        if not u:
            raise RecursoNoEncontrado('Unidad de cocina no encontrada')
        return u

    def crear(self, nombre: str, equivalencia_cantidad,
              equivalencia_unidad: str, grupo: str = 'VOLUMEN'):
        from dominio.entidades.unidad_cocina import UnidadCocina
        u = UnidadCocina(
            id=None, nombre=nombre,
            equivalencia_cantidad=Decimal(str(equivalencia_cantidad)),
            equivalencia_unidad=equivalencia_unidad,
            grupo=grupo,
        )
        return self.repo.guardar(u)

    def eliminar(self, unidad_id: int):
        u = self.repo.obtener_por_id(unidad_id)
        if not u:
            raise RecursoNoEncontrado('Unidad de cocina no encontrada')
        self.repo.eliminar(unidad_id)

    def convertir_a_unidad_base(self, cantidad, unidad_cocina_id):
        uc = self.obtener_por_id(unidad_cocina_id)
        return uc.convertir_a_base(Decimal(str(cantidad)))

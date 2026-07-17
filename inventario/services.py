from decimal import Decimal
from django.db import transaction
from dominio.puertos.repositorios import IInsumoRepository
from core.excepciones import (
    RecursoNoEncontrado, ReglaNegocioViolada,
)
from inventario.models import (
    Insumo, Receta, RecetaInsumo, MovimientoInsumo, UnidadConversion, convertir_unidad
)




class InsumoService:

    def obtener_queryset_api(self):
        from inventario.models import Insumo
        return Insumo.objects.all()

    def __init__(self, insumo_repo: IInsumoRepository):
        self.repo = insumo_repo

    def listar_insumos(self):
        return self.repo.listar()

    def obtener_por_id(self, insumo_id: int):
        insumo_domain = self.repo.obtener_por_id(insumo_id)
        if not insumo_domain:
            raise RecursoNoEncontrado('Insumo no encontrado')
        return insumo_domain

    def crear(self, nombre: str, unidad: str,
              stock_actual=Decimal('0'), stock_minimo=Decimal('0'),
              costo_unitario=Decimal('0')):
        from dominio.entidades.insumo import Insumo as InsumoDomain
        insumo_domain = InsumoDomain(
            id=None, nombre=nombre, unidad=unidad,
            stock_actual=stock_actual, stock_minimo=stock_minimo,
            costo_unitario=costo_unitario,
        )
        self.repo.guardar(insumo_domain)
        return Insumo.objects.get(nombre=nombre)

    def actualizar(self, insumo_id: int, **kwargs):
        insumo_domain = self.repo.obtener_por_id(insumo_id)
        if not insumo_domain:
            raise RecursoNoEncontrado('Insumo no encontrado')
        insumo_model = Insumo.objects.get(id=insumo_id)
        for attr, value in kwargs.items():
            setattr(insumo_model, attr, value)
        insumo_model.full_clean()
        insumo_model.save(update_fields=[
            'nombre', 'unidad', 'stock_actual',
            'stock_minimo', 'costo_unitario', 'actualizado_en',
        ])
        return insumo_model

    def eliminar(self, insumo_id: int):
        insumo_domain = self.repo.obtener_por_id(insumo_id)
        if not insumo_domain:
            raise RecursoNoEncontrado('Insumo no encontrado')
        self.repo.eliminar(insumo_id)

    @staticmethod
    @transaction.atomic
    def registrar_compra(insumo_id: int, unidad_conversion_id: int,
                         cantidad_unidades: int, costo_total: Decimal,
                         usuario=None):
        insumo = Insumo.objects.select_for_update().filter(id=insumo_id).first()
        if not insumo:
            raise RecursoNoEncontrado('Insumo no encontrado')
        uc = UnidadConversion.objects.get(id=unidad_conversion_id)
        cantidad_base = uc.convertir_a_base(cantidad_unidades)
        stock_anterior = insumo.stock_actual
        insumo.stock_actual += cantidad_base
        costo_unitario = (
            costo_total / cantidad_base if cantidad_base > 0 else Decimal('0')
        )
        insumo.costo_unitario = costo_unitario
        insumo.save(update_fields=['stock_actual', 'costo_unitario'])
        return MovimientoInsumo.objects.create(
            insumo=insumo, tipo='COMPRA',
            cantidad=cantidad_base,
            stock_anterior=stock_anterior,
            stock_posterior=insumo.stock_actual,
            usuario=usuario,
            observacion=f'Compra: {cantidad_unidades} {uc.nombre}',
            origen='COMPRA',
        )

    @staticmethod
    @transaction.atomic
    def ajustar_stock(insumo_id: int, nueva_cantidad: Decimal,
                      motivo: str, usuario=None):
        insumo = Insumo.objects.select_for_update().filter(id=insumo_id).first()
        if not insumo:
            raise RecursoNoEncontrado('Insumo no encontrado')
        stock_anterior = insumo.stock_actual
        diferencia = nueva_cantidad - stock_anterior
        insumo.stock_actual = nueva_cantidad
        insumo.save(update_fields=['stock_actual'])
        return MovimientoInsumo.objects.create(
            insumo=insumo, tipo='AJUSTE',
            cantidad=abs(diferencia),
            stock_anterior=stock_anterior,
            stock_posterior=insumo.stock_actual,
            usuario=usuario, observacion=motivo,
            origen='AJUSTE',
        )
    
class RecetaService:

    def listar_receta_insumos(self):
        from inventario.models import RecetaInsumo
        return RecetaInsumo.objects.select_related('receta', 'insumo').all()


    def obtener_queryset_api(self):
        from inventario.models import Receta
        return Receta.objects.all()

    def __init__(self, insumo_repo: IInsumoRepository):
        self.insumo_repo = insumo_repo

    def listar_recetas(self):
        return Receta.activos.prefetch_related('insumos__insumo').all()

    def obtener_por_id(self, receta_id: int):
        receta = Receta.objects.prefetch_related('insumos__insumo').filter(
            id=receta_id
        ).first()
        if not receta:
            raise RecursoNoEncontrado('Receta no encontrada')
        return receta

    @transaction.atomic
    def crear(self, nombre: str, insumos_data: list = None):
        receta, created = Receta.objects.get_or_create(nombre=nombre)
        if insumos_data and created:
            for item in insumos_data:
                RecetaInsumo.objects.get_or_create(
                    receta=receta,
                    insumo_id=item['insumo_id'],
                    defaults={
                        'cantidad_por_porcion': item['cantidad'],
                        'unidad': item.get('unidad', 'UNIDAD'),
                    }
                )
        return receta

    @transaction.atomic
    def actualizar(self, receta_id: int, nombre: str = None,
                   insumos_data: list = None):
        receta = self.obtener_por_id(receta_id)
        if nombre:
            receta.nombre = nombre
            receta.full_clean()
            receta.save(update_fields=['nombre'])
        if insumos_data:
            receta.insumos.all().update(activo=False)
            for item in insumos_data:
                ri, created = RecetaInsumo.objects.get_or_create(
                    receta=receta,
                    insumo_id=item['insumo_id'],
                    defaults={
                        'cantidad_por_porcion': item['cantidad'],
                        'unidad': item.get('unidad', 'UNIDAD'),
                    }
                )
                if not created:
                    ri.cantidad_por_porcion = item['cantidad']
                    ri.unidad = item.get('unidad', 'UNIDAD')
                    ri.activo = True
                    ri.save(update_fields=[
                        'cantidad_por_porcion', 'unidad', 'activo',
                        'actualizado_en',
                    ])
        return receta

    def eliminar_insumo(self, receta_insumo_id: int):
        try:
            ri = RecetaInsumo.objects.get(id=receta_insumo_id)
            ri.eliminar()
        except RecetaInsumo.DoesNotExist:
            raise RecursoNoEncontrado('Insumo de receta no encontrado')

    def eliminar(self, receta_id: int):
        receta = self.obtener_por_id(receta_id)
        receta.eliminar()

    def calcular_insumos_para_platos(self, receta_id: int,
                                     cantidad_platos: int) -> dict:
        receta = Receta.objects.filter(id=receta_id).first()
        if not receta:
            raise RecursoNoEncontrado('Receta no encontrada')
        resultado = {'insumos': [], 'disponible': True, 'faltantes': []}
        for ri in receta.insumos.select_related('insumo').all():
            necesario = (
                ri.cantidad_por_porcion * Decimal(str(cantidad_platos))
            )
            necesario_base = convertir_unidad(
                necesario, ri.unidad, ri.insumo.unidad
            )
            insumo_data = {
                'id': ri.insumo_id,
                'nombre': ri.insumo.nombre,
                'unidad': ri.insumo.unidad,
                'necesario': necesario_base,
                'stock_actual': ri.insumo.stock_actual,
                'suficiente': ri.insumo.stock_actual >= necesario_base,
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

    @staticmethod
    def convertir(unidad_origen_id: int, cantidad: Decimal,
                  unidad_destino_id: int = None) -> Decimal:
        """Convierte cantidad desde unidad_origen hasta unidad_destino
        (o hasta la unidad base si no se especifica)."""
        uo = UnidadConversion.objects.get(id=unidad_origen_id)
        return UnidadConversionService._convertir_recursivo(uo, cantidad, unidad_destino_id)

    @staticmethod
    def _convertir_recursivo(unidad: 'UnidadConversion', cantidad: Decimal,
                              destino_id: int = None) -> Decimal:
        if unidad.es_base:
            return cantidad
        if destino_id and unidad.id == destino_id:
            return cantidad
        total_en_sub = cantidad * unidad.contiene_cantidad
        return UnidadConversionService._convertir_recursivo(
            unidad.contiene_unidad, total_en_sub, destino_id
        )

    @staticmethod
    @transaction.atomic
    def crear_cadena(insumo_id: int, niveles: list) -> list:
        """Crea una cadena de unidades de conversión de abajo hacia arriba.
        niveles = [
            {'nombre': 'Paquete', 'contiene': 10, 'sub_unidad': 'Subpaquete'},
            {'nombre': 'Subpaquete', 'contiene': 500, 'sub_unidad': 'Gramo'},
        ]
        La última sub_unidad debe ser una unidad base existente.
        """
        niveles_procesados = []
        for nivel in reversed(niveles):
            sub = None
            try:
                sub = UnidadConversion.objects.get(
                    nombre=nivel['sub_unidad'], es_base=True
                )
            except UnidadConversion.DoesNotExist:
                sub = UnidadConversion.objects.filter(
                    nombre=nivel['sub_unidad'], insumo_id=insumo_id
                ).first()

            uc, _ = UnidadConversion.objects.get_or_create(
                insumo_id=insumo_id,
                nombre=nivel['nombre'],
                defaults={
                    'contiene_cantidad': nivel['contiene'],
                    'contiene_unidad': sub,
                    'es_base': False,
                }
            )
            niveles_procesados.append(uc)
        return list(reversed(niveles_procesados))

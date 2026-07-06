
from decimal import Decimal
from django.db import transaction
from django.db.models import F
from core.excepciones import (
    RecursoNoEncontrado, StockInsuficiente, ProductoSinStock,
    UnidadConversionInvalida, ReglaNegocioViolada,
)
from inventario.models import Insumo, Receta, RecetaInsumo, MovimientoInsumo, UnidadConversion
from menu.models import Plato


class InsumoService:
    @staticmethod
    @transaction.atomic
    def registrar_compra(insumo_id: int, unidad_conversion_id: int,
                         cantidad_unidades: int, costo_total: Decimal,
                         usuario=None) -> MovimientoInsumo:
        """Registra una compra de insumo usando la unidad de compra."""
        insumo = Insumo.objects.select_for_update().filter(id=insumo_id).first()
        if not insumo:
            raise RecursoNoEncontrado('Insumo no encontrado')

        uc = UnidadConversion.objects.get(id=unidad_conversion_id)
        cantidad_base = uc.convertir_a_base(cantidad_unidades)

        stock_anterior = insumo.stock_actual
        insumo.stock_actual += cantidad_base
        costo_unitario = costo_total / cantidad_base if cantidad_base > 0 else Decimal('0')
        insumo.costo_unitario = costo_unitario
        insumo.save(update_fields=['stock_actual', 'costo_unitario'])

        return MovimientoInsumo.objects.create(
            insumo=insumo, tipo='COMPRA',
            cantidad=cantidad_base,
            stock_anterior=stock_anterior,
            stock_posterior=insumo.stock_actual,
            usuario=usuario,
            observacion=f'Compra: {cantidad_unidades} {uc.nombre}',
        )

    @staticmethod
    @transaction.atomic
    def ajustar_stock(insumo_id: int, nueva_cantidad: Decimal,
                      motivo: str, usuario=None) -> MovimientoInsumo:
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
        )


class RecetaService:
    @staticmethod
    def calcular_insumos_para_platos(receta_id: int, cantidad_platos: int) -> dict:
        """Calcula los insumos necesarios para preparar N platos."""
        receta = Receta.objects.filter(id=receta_id).first()
        if not receta:
            raise RecursoNoEncontrado('Receta no encontrada')

        resultado = {'insumos': [], 'disponible': True, 'faltantes': []}
        for ri in receta.insumos.select_related('insumo').all():
            from inventario.models import convertir_unidad
            necesario = ri.cantidad_por_porcion * Decimal(str(cantidad_platos))
            necesario_base = convertir_unidad(necesario, ri.unidad, ri.insumo.unidad)
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

    @staticmethod
    def verificar_stock_para_plato(plato: Plato, cantidad: int = 1) -> bool:
        if not plato.receta_id:
            return True
        return RecetaService.calcular_insumos_para_platos(
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
    def crear_cadena(insumo_id: int, niveles: list) -> list:
        """Crea una cadena de unidades de conversión.
        niveles = [
            {'nombre': 'Paquete', 'contiene': 10, 'sub_unidad': 'Subpaquete'},
            {'nombre': 'Subpaquete', 'contiene': 500, 'sub_unidad': 'Gramo'},
        ]
        La última sub_unidad debe ser una unidad base existente.
        """
        cadenas = []
        for i, nivel in enumerate(niveles):
            es_ultimo = (i == len(niveles) - 1)
            sub = None
            if not es_ultimo:
                sub_nombre = niveles[i + 1]['nombre']
                sub = UnidadConversion.objects.filter(
                    nombre=sub_nombre, insumo_id=insumo_id
                ).first()
            else:
                sub = UnidadConversion.objects.get(
                    nombre=nivel['sub_unidad'], es_base=True
                )

            uc, _ = UnidadConversion.objects.get_or_create(
                insumo_id=insumo_id,
                nombre=nivel['nombre'],
                defaults={
                    'contiene_cantidad': nivel['contiene'],
                    'contiene_unidad': sub,
                    'es_base': False,
                }
            )
            cadenas.append(uc)
        return cadenas

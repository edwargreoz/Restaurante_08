

from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
from core.excepciones import UnidadConversionInvalida
from utils.models import ModeloBase


from dominio.entidades.unidad_conversion import UNIDADES_BASE, convertir_unidad

class Insumo(ModeloBase):

    UNIDADES = (
        ('UNIDAD', 'Unidad'),
        ('KG', 'Kilogramo'),
        ('GR', 'Gramo'),
        ('LT', 'Litro'),
        ('ML', 'Mililitro'),
    )

    nombre = models.CharField(
        max_length=200,
        unique=True,
        verbose_name='Nombre del insumo'
    )

    unidad = models.CharField(
        max_length=20,
        choices=UNIDADES,
        verbose_name='Unidad de medida'
    )

    stock_actual = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name='Stock actual'
    )

    stock_minimo = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='Stock minimo (alerta)'
    )

    costo_unitario = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name='Costo unitario (S/.)'
    )

    class Meta:
        ordering = ['nombre']
        verbose_name = 'Insumo'
        verbose_name_plural = 'Insumos'
        constraints = [
            models.CheckConstraint(
                check=models.Q(stock_actual__gte=0),
                name='stock_no_negativo'
            ),
        ]

    def __str__(self):
        return f'{self.nombre} ({self.stock_actual} {self.unidad})'


class Receta(ModeloBase):
    nombre = models.CharField(
        max_length=200,
        unique=True,
        verbose_name='Nombre de la receta'
    )

    class Meta:
        ordering = ['nombre']
        verbose_name = 'Receta'
        verbose_name_plural = 'Recetas'

    def __str__(self):
        return self.nombre


class RecetaInsumo(ModeloBase):

    receta = models.ForeignKey(
        Receta,
        on_delete=models.CASCADE,
        related_name='insumos',
        verbose_name='Receta'
    )

    insumo = models.ForeignKey(
        Insumo,
        on_delete=models.CASCADE,
        related_name='recetas',
        verbose_name='Insumo'
    )

    cantidad_por_porcion = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Cantidad por porcion'
    )

    unidad = models.CharField(
        max_length=20,
        choices=Insumo.UNIDADES,
        default='UNIDAD',
        verbose_name='Unidad en la receta'
    )

    unidad_cocina = models.ForeignKey(
        'UnidadCocina',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='receta_insumos',
        verbose_name='Unidad de cocina'
    )

    class Meta:
        verbose_name = 'Insumo de Receta'
        verbose_name_plural = 'Insumos de Recetas'
        # Un insumo solo puede aparecer una vez por receta
        unique_together = ('receta', 'insumo')

    def __str__(self):
        return f'{self.receta.nombre} -> {self.cantidad_por_porcion} {self.unidad} de {self.insumo.nombre}'


class MovimientoInsumo(ModeloBase):
    TIPOS = (
        ('DEDUCCION', 'Deducción por comanda'),
        ('REPOSICION', 'Reposición por anulación'),
        ('AJUSTE', 'Ajuste manual'),
        ('COMPRA', 'Compra / Ingreso'),
    )

    ORIGENES = (
        ('COMANDA', 'Comanda'),
        ('COMPRA', 'Compra'),
        ('AJUSTE', 'Ajuste'),
        ('SISTEMA', 'Sistema'),
    )

    insumo = models.ForeignKey(
        Insumo, on_delete=models.CASCADE,
        related_name='movimientos',
        verbose_name='Insumo'
    )
    comanda = models.ForeignKey(
        'pedidos.Comanda', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='movimientos_insumo',
        verbose_name='Comanda relacionada'
    )
    tipo = models.CharField(
        max_length=20, choices=TIPOS,
        verbose_name='Tipo de movimiento'
    )
    cantidad = models.DecimalField(
        max_digits=10, decimal_places=2,
        verbose_name='Cantidad (valor absoluto)'
    )
    stock_anterior = models.DecimalField(
        max_digits=10, decimal_places=2,
        verbose_name='Stock antes del movimiento'
    )
    stock_posterior = models.DecimalField(
        max_digits=10, decimal_places=2,
        verbose_name='Stock después del movimiento'
    )
    usuario = models.ForeignKey(
        'auth.User', on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name='Usuario que realizó el movimiento'
    )
    observacion = models.TextField(
        blank=True, verbose_name='Observación'
    )
    fecha = models.DateTimeField(
        auto_now_add=True, verbose_name='Fecha del movimiento'
    )
    origen = models.CharField(
        max_length=20, choices=ORIGENES,
        default='SISTEMA',
        verbose_name='Origen del movimiento'
    )

    class Meta:
        ordering = ['-fecha']
        verbose_name = 'Movimiento de Insumo'
        verbose_name_plural = 'Movimientos de Insumos'

    def __str__(self):
        return f'{self.get_tipo_display()} - {self.insumo.nombre} ({self.cantidad})'


class UnidadConversion(ModeloBase):
    nombre = models.CharField(max_length=100, verbose_name='Nombre de la unidad')
    es_base = models.BooleanField(default=False, verbose_name='¿Es unidad base?')
    insumo = models.ForeignKey(
        'Insumo', on_delete=models.CASCADE,
        related_name='unidades_conversion',
        null=True, blank=True,
        verbose_name='Insumo asociado (solo si no es base)',
    )
    contiene_cantidad = models.DecimalField(
        max_digits=10, decimal_places=2,
        null=True, blank=True,
        verbose_name='Cantidad que contiene de la subunidad',
    )
    contiene_unidad = models.ForeignKey(
        'self', on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='unidad_padre',
        verbose_name='Subunidad que contiene',
    )

    class Meta:
        verbose_name = 'Conversión de Unidad'
        verbose_name_plural = 'Conversiones de Unidades'
        unique_together = ('nombre', 'insumo')

    def __str__(self):
        if self.es_base:
            return f'Base: {self.nombre}'
        return f'1 {self.nombre} = {self.contiene_cantidad} {self.contiene_unidad.nombre if self.contiene_unidad else "?"}'

    def convertir_a_base(self, cantidad: Decimal) -> Decimal:
        from decimal import Decimal
        if self.es_base:
            return cantidad
        if not self.contiene_unidad:
            raise UnidadConversionInvalida(f'{self.nombre} no tiene subunidad definida')
        total_en_sub = cantidad * self.contiene_cantidad
        return self.contiene_unidad.convertir_a_base(total_en_sub)

    def convertir_desde_base(self, cantidad_base: Decimal) -> Decimal:
        if self.es_base:
            return cantidad_base
        if not self.contiene_unidad:
            raise UnidadConversionInvalida(f'{self.nombre} no tiene subunidad definida')
        en_sub = self.contiene_unidad.convertir_desde_base(cantidad_base)
        return en_sub / self.contiene_cantidad


class UnidadCocina(ModeloBase):
    GRUPOS = (
        ('VOLUMEN', 'Volumen'),
        ('PESO', 'Peso'),
        ('CANTIDAD', 'Cantidad'),
    )

    nombre = models.CharField(max_length=100, unique=True, verbose_name='Nombre')
    equivalencia_cantidad = models.DecimalField(
        max_digits=10, decimal_places=2,
        verbose_name='Cantidad equivalente en unidad base'
    )
    equivalencia_unidad = models.CharField(
        max_length=20, choices=Insumo.UNIDADES,
        verbose_name='Unidad base de equivalencia'
    )
    grupo = models.CharField(
        max_length=20, choices=GRUPOS,
        default='VOLUMEN',
        verbose_name='Grupo'
    )

    class Meta:
        ordering = ['nombre']
        verbose_name = 'Unidad de Cocina'
        verbose_name_plural = 'Unidades de Cocina'

    def __str__(self):
        return f'{self.nombre} ({self.equivalencia_cantidad} {self.equivalencia_unidad})'


class PresentacionInsumo(ModeloBase):
    insumo = models.ForeignKey(
        Insumo, on_delete=models.CASCADE,
        related_name='presentaciones',
        verbose_name='Insumo'
    )
    nombre = models.CharField(max_length=200, verbose_name='Nombre de la presentación')
    cantidad = models.DecimalField(
        max_digits=10, decimal_places=2,
        verbose_name='Cantidad contenida'
    )
    unidad_medida = models.CharField(
        max_length=20, choices=Insumo.UNIDADES,
        verbose_name='Unidad de medida'
    )
    costo_compra = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='Costo de compra (S/)'
    )
    es_principal = models.BooleanField(
        default=False,
        verbose_name='¿Es presentación principal?'
    )

    class Meta:
        ordering = ['nombre']
        verbose_name = 'Presentación de Insumo'
        verbose_name_plural = 'Presentaciones de Insumos'

    def __str__(self):
        return f'{self.nombre} ({self.cantidad} {self.unidad_medida})'

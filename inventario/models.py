

from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal


UNIDADES_BASE = {
    'UNIDAD': ('UNIDAD', Decimal('1')),
    'KG': ('GR', Decimal('1000')),
    'GR': ('GR', Decimal('1')),
    'LT': ('ML', Decimal('1000')),
    'ML': ('ML', Decimal('1')),
}


def convertir_unidad(cantidad, de_unidad, a_unidad):
    if de_unidad == a_unidad:
        return cantidad
    base_de, factor_de = UNIDADES_BASE[de_unidad]
    base_a, factor_a = UNIDADES_BASE[a_unidad]
    if base_de != base_a:
        raise ValueError(
            f"No se puede convertir {de_unidad} a {a_unidad}: "
            f"son categorias diferentes"
        )
    en_base = cantidad * factor_de
    return en_base / factor_a

class Insumo(models.Model):

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


class RecetaInsumo(models.Model):

    plato = models.ForeignKey(
        'menu.Plato',
        on_delete=models.CASCADE,
        related_name='receta',
        verbose_name='Plato'
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

    class Meta:
        verbose_name = 'Receta de Insumo'
        verbose_name_plural = 'Recetas de Insumos'
        # Un insumo solo puede aparecer una vez por plato
        unique_together = ('plato', 'insumo')

    def __str__(self):
        return f'{self.plato.nombre} -> {self.cantidad_por_porcion} {self.insumo.unidad} de {self.insumo.nombre}'


class MovimientoInsumo(models.Model):
    TIPOS = (
        ('DEDUCCION', 'Deducción por comanda'),
        ('REPOSICION', 'Reposición por anulación'),
        ('AJUSTE', 'Ajuste manual'),
        ('COMPRA', 'Compra / Ingreso'),
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

    class Meta:
        ordering = ['-fecha']
        verbose_name = 'Movimiento de Insumo'
        verbose_name_plural = 'Movimientos de Insumos'

    def __str__(self):
        return f'{self.get_tipo_display()} - {self.insumo.nombre} ({self.cantidad})'

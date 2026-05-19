

from django.db import models
from django.core.validators import MinValueValidator


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

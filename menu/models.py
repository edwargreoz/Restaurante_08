
from django.db import models
from django.core.validators import MinValueValidator
from inventario.models import Receta

class Categoria(models.Model):

    nombre = models.CharField(
        max_length=100,
        verbose_name='Nombre de la categoria'
    )

    es_bebida = models.BooleanField(
        default=False,
        verbose_name='Es bebida?'
    )

    orden_display = models.IntegerField(
        default=0,
        verbose_name='Orden de visualizacion'
    )

    class Meta:
        ordering = ['orden_display']
        verbose_name = 'Categoria'
        verbose_name_plural = 'Categorias'

    def __str__(self):
        return self.nombre


class Plato(models.Model):

    nombre = models.CharField(
        max_length=200,
        verbose_name='Nombre del plato'
    )

    descripcion = models.TextField(
        blank=True,
        verbose_name='Descripcion'
    )

    precio = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name='Precio (S/.)'
    )

    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.CASCADE,
        related_name='platos',
        verbose_name='Categoria'
    )

    receta = models.ForeignKey(
        Receta,
        on_delete=models.PROTECT,
        related_name='platos',
        verbose_name='Receta'
    )

    tiempo_preparacion_min = models.IntegerField(
        default=15,
        verbose_name='Tiempo de preparacion (minutos)'
    )

    disponible = models.BooleanField(
        default=True,
        verbose_name='Disponible?'
    )

    imagen = models.ImageField(
        upload_to='platos/',
        blank=True,
        null=True,
        verbose_name='Imagen del plato'
    )

    class Meta:
        ordering = ['categoria__orden_display', 'nombre']
        verbose_name = 'Plato'
        verbose_name_plural = 'Platos'

    def __str__(self):
        return f'{self.nombre} - S/ {self.precio}'

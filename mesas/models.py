

from django.db import models


class Mesa(models.Model):
    """
    Representa una mesa fisica en el salon del restaurante.
    Cada mesa tiene un numero unico, capacidad, zona y estado.
    """
    # Opciones de zona del salon
    ZONAS = (
        ('SALON', 'Salon Principal'),
        ('TERRAZA', 'Terraza'),
        ('VIP', 'VIP'),
    )

    # Opciones de estado de la mesa
    ESTADOS = (
        ('LIBRE', 'Libre'),
        ('OCUPADA', 'Ocupada'),
        ('RESERVADA', 'Reservada'),
        ('LIMPIEZA', 'Limpieza'),
    )

    numero = models.IntegerField(
        unique=True,
        verbose_name='Numero de mesa'
    )

    capacidad = models.IntegerField(
        verbose_name='Capacidad maxima de personas'
    )

    zona = models.CharField(
        max_length=20,
        choices=ZONAS,
        default='SALON',
        verbose_name='Zona del salon'
    )

    estado = models.CharField(
        max_length=20,
        choices=ESTADOS,
        default='LIBRE',
        verbose_name='Estado actual'
    )

    class Meta:
        """Configuracion del modelo."""
        ordering = ['numero']
        verbose_name = 'Mesa'
        verbose_name_plural = 'Mesas'

    def __str__(self):
        """Representacion en texto: 'Mesa 5 (Ocupada)'."""
        return f'Mesa {self.numero} ({self.get_estado_display()})'

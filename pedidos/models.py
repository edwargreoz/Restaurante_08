from django.db import models
from utils.models import ModeloBase

class Comanda(ModeloBase):
    """
    Comanda o pedido realizado en una mesa.
    Agrupa todas las lineas de pedido de una misma mesa.
    """

    ESTADOS = (
        ('ABIERTA', 'Abierta'),
        ('EN_PREPARACION', 'En Preparacion'),
        ('LISTA', 'Lista'),
        ('COBRADA', 'Cobrada'),
        ('ANULADA', 'Anulada'),
    )

    mesa = models.ForeignKey(
        'mesas.Mesa',
        on_delete=models.CASCADE,
        related_name='comandas',
        verbose_name='Mesa'
    )

    mozo = models.ForeignKey(
        'auth.User',
        on_delete=models.CASCADE,
        verbose_name='Mozo que atiende',
        related_name='comandas_atendidas'
    )

    estado = models.CharField(
        max_length=20,
        choices=ESTADOS,
        default='ABIERTA',
        verbose_name='Estado de la comanda'
    )

    fecha_apertura = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de apertura'
    )

    fecha_cierre = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Fecha de cierre'
    )

    class Meta:
        ordering = ['-fecha_apertura']
        verbose_name = 'Comanda'
        verbose_name_plural = 'Comandas'
        indexes = [
            models.Index(fields=['mesa', 'estado']),
        ]

    def __str__(self):
        return f'Comanda #{self.id} - Mesa {self.mesa.numero} ({self.get_estado_display()})'
    
    @property
    def total(self):
        return self.lineas.aggregate(
            total=models.Sum(models.F('cantidad') * models.F('plato__precio'))
        )['total'] or 0

class LineaComanda(ModeloBase):
    """
    Linea individual de una comanda.
    Representa un plato con su cantidad y estado de preparacion.
    """

    ESTADOS = (
        ('PENDIENTE', 'Pendiente'),
        ('EN_PREP', 'En Preparacion'),
        ('LISTO', 'Listo'),
        ('ENTREGADO', 'Entregado'),
    )

    comanda = models.ForeignKey(
        Comanda,
        on_delete=models.CASCADE,
        related_name='lineas',
        verbose_name='Comanda'
    )

    plato = models.ForeignKey(
        'menu.Plato',
        on_delete=models.CASCADE,
        verbose_name='Plato'
    )

    cantidad = models.IntegerField(
        default=1,
        verbose_name='Cantidad'
    )

    observacion = models.TextField(
        blank=True,
        verbose_name='Observacion (ej: sin cebolla)'
    )

    estado = models.CharField(
        max_length=20,
        choices=ESTADOS,
        default='PENDIENTE',
        verbose_name='Estado de preparacion'
    )

    class Meta:
        verbose_name = 'Linea de Comanda'
        verbose_name_plural = 'Lineas de Comanda'

    def __str__(self):
        return f'{self.cantidad}x {self.plato.nombre} ({self.get_estado_display()})'
     
    @property
    def subtotal(self):
        return self.cantidad * self.plato.precio

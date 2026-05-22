
from django.db import models
from django.db.models import Sum, Count

class PagoManager(models.Manager):
    def reporte_ventas(self, caja_id=None, fecha_desde=None, fecha_hasta=None):
        pagos = self.all()
        if caja_id:
            pagos = pagos.filter(caja_id=caja_id)
        if fecha_desde:
            pagos = pagos.filter(fecha__date__gte=fecha_desde)
        if fecha_hasta:
            pagos = pagos.filter(fecha__date__lte=fecha_hasta)
        totales_metodo = pagos.values('metodo').annotate(
            total=Sum('monto'), cantidad=Count('id')
        )
        return {
            'total_general': pagos.aggregate(total=Sum('monto'))['total'] or 0,
            'total_pagos': pagos.count(),
            'por_metodo': totales_metodo,
        }
    
class Caja(models.Model):
    """
    Registro de apertura y cierre de turno de caja.
    Controla el saldo inicial y final de cada turno.
    """

    # Estados del turno de caja
    ESTADOS = (
        ('ABIERTA', 'Abierta'),
        ('CERRADA', 'Cerrada'),
    )

    turno = models.CharField(
        max_length=50,
        verbose_name='Nombre del turno (ej: TARDE)'
    )

    cajero = models.ForeignKey(
        'auth.User',
        on_delete=models.CASCADE,
        verbose_name='Cajero responsable'
    )

    saldo_inicial = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Saldo inicial (S/.)'
    )

    estado = models.CharField(
        max_length=20,
        choices=ESTADOS,
        default='ABIERTA',
        verbose_name='Estado del turno'
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
        verbose_name = 'Caja'
        verbose_name_plural = 'Cajas'

    def __str__(self):
        return f'{self.turno} - {self.cajero.username} ({self.get_estado_display()})'
    


class Pago(models.Model):
    """
    Registro de pago de una comanda.
    Almacena el metodo, monto y vuelto calculado.
    """

    # Metodos de pago aceptados
    METODOS = (
        ('EFECTIVO', 'Efectivo'),
        ('TARJETA', 'Tarjeta de credito/debito'),
        ('YAPE', 'Yape'),
        ('PLIN', 'Plin'),
    )

    comanda = models.ForeignKey(
        'pedidos.Comanda',
        on_delete=models.CASCADE,
        related_name='pagos',
        verbose_name='Comanda'
    )
    caja = models.ForeignKey(
        'Caja', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='pagos',
        verbose_name='Turno de caja'
    )   

    metodo = models.CharField(
        max_length=20,
        choices=METODOS,
        verbose_name='Metodo de pago'
    )

    monto = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Monto recibido (S/.)'
    )

    vuelto = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='Vuelto (S/.)'
    )

    referencia = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Referencia (ej: VISA ****1234)'
    )

    fecha = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha del pago'
    )
    objects = PagoManager()

    class Meta:
        ordering = ['-fecha']
        verbose_name = 'Pago'
        verbose_name_plural = 'Pagos'

    def __str__(self):
        return f'{self.metodo} - S/ {self.monto} (Comanda #{self.comanda_id})'

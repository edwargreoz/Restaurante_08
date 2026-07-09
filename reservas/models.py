from django.db import models
from django.core.validators import MinValueValidator
from utils.models import ModeloBase


class Reserva(ModeloBase):
    mesa = models.ForeignKey(
        'mesas.Mesa', on_delete=models.CASCADE,
        related_name='reservas', null=True, blank=True
    )
    union_mesa = models.ForeignKey(
        'mesas.UnionMesa', on_delete=models.CASCADE,
        related_name='reservas', null=True, blank=True
    )
    cliente_nombre = models.CharField(max_length=200)
    cliente_contacto = models.CharField(max_length=100, blank=True)
    fecha = models.DateField()
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    num_personas = models.IntegerField(validators=[MinValueValidator(1)])
    observacion = models.TextField(blank=True)
    finalizada = models.BooleanField(default=False)

    class Meta:
        ordering = ['-fecha', 'hora_inicio']
        verbose_name = 'Reserva'
        verbose_name_plural = 'Reservas'

    def __str__(self):
        if self.finalizada:
            estado = 'Finalizada'
        else:
            estado = 'Activa' if self.activo else 'Cancelada'
        if self.union_mesa:
            return f'{self.cliente_nombre} - Unión: {self.union_mesa} ({self.fecha}) - {estado}'
        else:
            return f'{self.cliente_nombre} - Mesa {self.mesa.numero} ({self.fecha}) - {estado}'

    def cancelar(self):
        self.activo = False
        self.save(update_fields=['activo'])

        if self.mesa:
            tiene_otra_reserva = Reserva.objects.filter(
                mesa=self.mesa, activo=True
            ).exclude(id=self.id).exists()
            if not tiene_otra_reserva:
                self.mesa.estado = 'LIBRE'
                self.mesa.save(update_fields=['estado'])
        elif self.union_mesa:
            tiene_otra_reserva = Reserva.objects.filter(
                union_mesa=self.union_mesa, activo=True
            ).exclude(id=self.id).exists()
            if not tiene_otra_reserva:
                for m in self.union_mesa.mesas.all():
                    m.estado = 'LIBRE'
                    m.save(update_fields=['estado'])
                self.union_mesa.activo = False
                self.union_mesa.save(update_fields=['activo'])

    def finalizar(self):
        self.activo = False
        self.finalizada = True
        self.save(update_fields=['activo', 'finalizada'])

        if self.mesa:
            tiene_otra_reserva = Reserva.objects.filter(
                mesa=self.mesa, activo=True
            ).exclude(id=self.id).exists()
            if not tiene_otra_reserva:
                self.mesa.estado = 'LIMPIEZA'
                self.mesa.save(update_fields=['estado'])
        elif self.union_mesa:
            tiene_otra_reserva = Reserva.objects.filter(
                union_mesa=self.union_mesa, activo=True
            ).exclude(id=self.id).exists()
            if not tiene_otra_reserva:
                for m in self.union_mesa.mesas.all():
                    m.estado = 'LIMPIEZA'
                    m.save(update_fields=['estado'])
                self.union_mesa.activo = False
                self.union_mesa.save(update_fields=['activo'])

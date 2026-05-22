from django.db import models
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone


class Reserva(models.Model):
    mesa = models.ForeignKey(
        'mesas.Mesa', on_delete=models.CASCADE,
        related_name='reservas'
    )
    cliente_nombre = models.CharField(max_length=200)
    cliente_contacto = models.CharField(max_length=100, blank=True)
    fecha = models.DateField()
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    num_personas = models.IntegerField(validators=[MinValueValidator(1)])
    observacion = models.TextField(blank=True)
    activa = models.BooleanField(default=True)
    creado_por = models.ForeignKey(
        'auth.User', on_delete=models.SET_NULL, null=True
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha', 'hora_inicio']
        verbose_name = 'Reserva'
        verbose_name_plural = 'Reservas'

    def __str__(self):
        estado = 'Activa' if self.activa else 'Cancelada'
        return f'{self.cliente_nombre} - Mesa {self.mesa.numero} ({self.fecha}) - {estado}'

    def clean(self):
        if self.hora_inicio and self.hora_fin and self.hora_inicio >= self.hora_fin:
            raise ValidationError('La hora de inicio debe ser menor a la hora de fin')
        if self.num_personas and self.mesa and self.num_personas > self.mesa.capacidad:
            raise ValidationError(f'La mesa solo tiene capacidad para {self.mesa.capacidad} personas')

    def save(self, *args, **kwargs):
        self.full_clean()
        es_nueva = self.pk is None
        super().save(*args, **kwargs)
        if es_nueva and self.activa:
            self.mesa.estado = 'RESERVADA'
            self.mesa.save(update_fields=['estado'])

    def cancelar(self):
        self.activa = False
        self.save(update_fields=['activa'])
        tiene_otra_reserva = Reserva.objects.filter(
            mesa=self.mesa, activa=True
        ).exclude(id=self.id).exists()
        if not tiene_otra_reserva:
            self.mesa.estado = 'LIBRE'
            self.mesa.save(update_fields=['estado'])

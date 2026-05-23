
from django.db import models
from django.core.validators import MinValueValidator

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
        validators= [MinValueValidator(1)],
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

class UnionMesa(models.Model):
    """Con esta clase vamos a poder unir mesas 
    fisicamente para un grupo de comenzales
    """
    mesas = models.ManyToManyField(
        'Mesa',
        related_name='uniones',
        verbose_name='Mesas que componen la union'
    )
           
    activa = models.BooleanField(
        default=True,
        verbose_name='¿La union esta activa?'
    )
    
    fecha_creacion= models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de Creacion'
    )   
    class Meta:
        verbose_name= 'Union de Mesas'
        verbose_name_plural='Uniones de Mesas'
    
    def capacidad_total(self):
        return sum(m.capacidad for m in self.mesas.all())
        
    def ocupantes_maximos(self):
        return self.capacidad_total()
        
    def esta_reservada(self):
        return self.reservas.filter(activa=True).exists()
        
    def __str__(self):
        mesas_str = ' + '.join(
            [f'Mesa {m.numero}' for m in self.mesas.all()]
        )
        return f'{mesas_str} ({self.ocupantes_maximos()} pax)'





    

    

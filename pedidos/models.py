

from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone


class Comanda(models.Model):
    """
    Comanda o pedido realizado en una mesa.
    Agrupa todas las lineas de pedido de una misma mesa.
    """

    # Estados posibles de una comanda
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
        verbose_name='Mozo que atiende'
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
        # Indice compuesto para buscar comandas activas por mesa
        indexes = [
            models.Index(fields=['mesa', 'estado']),
        ]

    def __str__(self):
        return f'Comanda #{self.id} - Mesa {self.mesa.numero} ({self.get_estado_display()})'
    
    @property
    def total(self):
        return sum(
            linea.cantidad * linea.plato.precio
            for linea in self.lineas.all()
        )
    @classmethod
    def abrir(cls, mesa_id, usuario):
        from mesas.models import Mesa, UnionMesa
        mesa = Mesa.objects.filter(id=mesa_id).first()
        if not mesa:
            raise ValidationError('Mesa no encontrada')
        if mesa.estado != 'LIBRE':
            raise ValidationError('La mesa no esta libre')
        union = UnionMesa.objects.filter(mesas=mesa, activa=True).first()
        if union:
            for m in union.mesas.all():
                if m.estado != 'LIBRE':
                    raise ValidationError(
                        f'La mesa {m.numero} de la union no esta libre'
                    )
        comanda = cls.objects.create(mesa=mesa, mozo=usuario)
        mesa.estado = 'OCUPADA'
        mesa.save()
        if union:
            for m in union.mesas.all():
                if m.id != mesa.id:
                    m.estado = 'OCUPADA'
                    m.save()
        return comanda
    
    def agregar_platos(self, platos_data):
        from menu.models import Plato
        from inventario.models import RecetaInsumo
        if self.estado not in ('ABIERTA', 'LISTA'):
            raise ValidationError('La comanda no esta abierta')
        errores = []
        platos_a_crear = []
        for item in platos_data:
            plato_id = item.get('plato_id')
            cantidad = item.get('cantidad', 1)
            observacion = item.get('observacion', '')
            plato = Plato.objects.filter(id=plato_id).first()
            if not plato:
                errores.append({'plato_id': plato_id, 'error': 'Plato no encontrado'})
                continue
            if not plato.disponible:
                errores.append({'plato_id': plato_id, 'error': 'Plato no disponible'})
                continue
            recetas = RecetaInsumo.objects.filter(plato=plato)
            faltantes = []
            for receta in recetas:
                necesario = receta.cantidad_por_porcion * cantidad
                if receta.insumo.stock_actual < necesario:
                    faltantes.append(
                        f"{receta.insumo.nombre}: disponible "
                        f"{receta.insumo.stock_actual}, necesario {necesario}"
                    )
            if faltantes:
                errores.append({
                    'plato_id': plato_id,
                    'plato': plato.nombre,
                    'error': 'Stock insuficiente',
                    'detalle': faltantes
                })
                continue
            platos_a_crear.append(LineaComanda(
                comanda=self, plato=plato,
                cantidad=cantidad, observacion=observacion,
            ))
        if errores:
            raise ValidationError({'errores': errores})
        LineaComanda.objects.bulk_create(platos_a_crear)
        return platos_a_crear
    def pagar(self, metodo, monto, vuelto=0, referencia=''):
        from caja.models import Pago
        from inventario.models import RecetaInsumo
        from mesas.models import UnionMesa
        if self.estado not in ('ABIERTA', 'LISTA'):
            raise ValidationError('La comanda no esta lista para pagar')
        for linea in self.lineas.all():
            for receta in RecetaInsumo.objects.filter(plato=linea.plato):
                receta.insumo.stock_actual -= receta.cantidad_por_porcion * linea.cantidad
                receta.insumo.save()
        Pago.objects.create(
            comanda=self, metodo=metodo,
            monto=monto, vuelto=vuelto, referencia=referencia
        )
        self.estado = 'COBRADA'
        self.fecha_cierre = timezone.now()
        self.save()
        mesa = self.mesa
        mesa.estado = 'LIBRE'
        mesa.save()
        union = UnionMesa.objects.filter(mesas=mesa, activa=True).first()
        if union:
            for m in union.mesas.all():
                if m.id != mesa.id:
                    m.estado = 'LIBRE'
                    m.save()
        return self
    def pagar_split(self, pagos_lista):
        from caja.models import Pago
        from inventario.models import RecetaInsumo
        from mesas.models import UnionMesa
        if self.estado not in ('ABIERTA', 'LISTA'):
            raise ValidationError('La comanda no esta lista para pagar')
        total_pagos = sum(p['monto'] for p in pagos_lista)
        if abs(total_pagos - self.total) > 0.01:
            raise ValidationError(
                f'Suma de pagos ({total_pagos}) no coincide con total ({self.total})'
            )
        for linea in self.lineas.all():
            for receta in RecetaInsumo.objects.filter(plato=linea.plato):
                receta.insumo.stock_actual -= receta.cantidad_por_porcion * linea.cantidad
                receta.insumo.save()
        for pd in pagos_lista:
            Pago.objects.create(
                comanda=self, metodo=pd['metodo'],
                monto=pd['monto'], vuelto=pd.get('vuelto', 0),
                referencia=pd.get('referencia', '')
            )
        self.estado = 'COBRADA'
        self.fecha_cierre = timezone.now()
        self.save()
        mesa = self.mesa
        mesa.estado = 'LIBRE'
        mesa.save()
        union = UnionMesa.objects.filter(mesas=mesa, activa=True).first()
        if union:
            for m in union.mesas.all():
                if m.id != mesa.id:
                    m.estado = 'LIBRE'
                    m.save()
        return self

class LineaComanda(models.Model):
    """
    Linea individual de una comanda.
    Representa un plato con su cantidad y estado de preparacion.
    """

    # Estados de cada linea de comanda (para el KDS)
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
    def enviar_cocina(self):
        if self.estado != 'PENDIENTE':
            raise ValidationError(
                'Solo se puede enviar a cocina en estado PENDIENTE'
            )
        self.estado = 'EN_PREP'
        self.save(update_fields=['estado'])
        comanda = self.comanda
        if all(l.estado == 'EN_PREP' for l in comanda.lineas.all()):
            comanda.estado = 'EN_PREPARACION'
            comanda.save(update_fields=['estado'])
        return self
    
    def marcar_listo(self):
        if self.estado != 'EN_PREP':
            raise ValidationError(
                'Solo se puede marcar LISTO una linea EN_PREPARACION'
            )
        self.estado = 'LISTO'
        self.save(update_fields=['estado'])
        comanda = self.comanda
        if all(l.estado == 'LISTO' for l in comanda.lineas.all()):
            comanda.estado = 'LISTA'
            comanda.save(update_fields=['estado'])
        return self



from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal
from inventario.models import RecetaInsumo, MovimientoInsumo, convertir_unidad
from mesas.models import Mesa, UnionMesa
from caja.models import Pago
from menu.models import Plato


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
        return self.lineas.aggregate(
            total=models.Sum(models.F('cantidad') * models.F('plato__precio'))
        )['total'] or 0
    @classmethod
    def abrir(cls, mesa_id, usuario):
        from django.db import transaction
        from caja.models import Caja
        with transaction.atomic():
            caja_abierta = Caja.objects.filter(estado='ABIERTA').exists()
            if not caja_abierta:
                raise ValidationError('No hay un turno de caja abierto. Abre caja primero.')
            mesa = Mesa.objects.select_for_update().filter(id=mesa_id).first()
            if not mesa:
                raise ValidationError('Mesa no encontrada')
            comanda_existente = cls.objects.filter(
                mesa=mesa, estado__in=['ABIERTA', 'EN_PREPARACION', 'LISTA']
            ).first()
            if comanda_existente:
                return comanda_existente
            if mesa.estado not in ['LIBRE', 'RESERVADA']:
                raise ValidationError('La mesa no esta libre ni reservada')
            union = UnionMesa.objects.filter(mesas=mesa, activa=True).first()
            if union:
                for m in union.mesas.all():
                    comanda_m = cls.objects.filter(
                        mesa=m, estado__in=['ABIERTA', 'EN_PREPARACION', 'LISTA']
                    ).first()
                    if comanda_m:
                        return comanda_m
                    if m.estado not in ['LIBRE', 'RESERVADA']:
                        raise ValidationError(
                            f'La mesa {m.numero} de la union no esta libre ni reservada'
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
    
    def agregar_platos(self, platos_data, usuario=None):
        from django.db import transaction
        if self.estado not in ('ABIERTA', 'LISTA'):
            raise ValidationError('La comanda no esta abierta')
        with transaction.atomic():
            errores = []
            platos_a_crear = []
            movimientos = []
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
                if not plato.receta_id:
                    errores.append({
                        'plato_id': plato_id,
                        'plato': plato.nombre,
                        'error': 'El plato no tiene una receta asignada'
                    })
                    continue
                recetas = plato.receta.insumos.select_related(
                    'insumo'
                ).select_for_update(of=('insumo',))
                faltantes = []
                deducciones = []
                for receta in recetas:
                    insumo = receta.insumo
                    necesario_en_unidad_receta = receta.cantidad_por_porcion * Decimal(str(cantidad))
                    necesario = convertir_unidad(
                        necesario_en_unidad_receta,
                        receta.unidad,
                        insumo.unidad
                    )
                    if insumo.stock_actual < necesario:
                        faltantes.append(
                            f"{insumo.nombre}: disponible "
                            f"{insumo.stock_actual} {insumo.unidad}, "
                            f"necesario {necesario} {insumo.unidad}"
                        )
                        continue
                    stock_anterior = insumo.stock_actual
                    insumo.stock_actual -= necesario
                    insumo.save(update_fields=['stock_actual'])
                    deducciones.append(MovimientoInsumo(
                        insumo=insumo,
                        comanda=self,
                        tipo='DEDUCCION',
                        cantidad=necesario,
                        stock_anterior=stock_anterior,
                        stock_posterior=insumo.stock_actual,
                        usuario=usuario,
                        observacion=f"Plato: {plato.nombre} x{cantidad}"
                    ))
                if faltantes:
                    errores.append({
                        'plato_id': plato_id,
                        'plato': plato.nombre,
                        'error': 'Stock insuficiente',
                        'detalle': faltantes
                    })
                    continue
                movimientos.extend(deducciones)
                platos_a_crear.append(LineaComanda(
                    comanda=self, plato=plato,
                    cantidad=cantidad, observacion=observacion,
                ))
            if errores:
                raise ValidationError({'errores': errores})
            LineaComanda.objects.bulk_create(platos_a_crear)
            MovimientoInsumo.objects.bulk_create(movimientos)
        return platos_a_crear
    def fusionar(self, otra_comanda):
        if self.estado in ('COBRADA', 'ANULADA'):
            raise ValidationError('La comanda principal no esta activa')
        if otra_comanda.estado in ('COBRADA', 'ANULADA'):
            raise ValidationError('La comanda a fusionar no esta activa')
        LineaComanda.objects.filter(comanda=otra_comanda).update(comanda=self)
        otra_comanda.estado = 'ANULADA'
        otra_comanda.fecha_cierre = timezone.now()
        otra_comanda.save(update_fields=['estado', 'fecha_cierre'])

    def anular(self, usuario=None):
        from django.db import transaction
        if self.estado == 'COBRADA':
            raise ValidationError('No se puede anular una comanda ya cobrada')
        if self.estado == 'ANULADA':
            raise ValidationError('La comanda ya esta anulada')
        with transaction.atomic():
            lineas = self.lineas.select_related('plato').all()
            movimientos = []
            for linea in lineas:
                if not linea.plato.receta_id:
                    continue
                recetas = linea.plato.receta.insumos.select_related(
                    'insumo'
                ).select_for_update(of=('insumo',))
                for receta in recetas:
                    insumo = receta.insumo
                    cantidad_en_unidad_receta = receta.cantidad_por_porcion * Decimal(str(linea.cantidad))
                    cantidad_a_restaurar = convertir_unidad(
                        cantidad_en_unidad_receta,
                        receta.unidad,
                        insumo.unidad
                    )
                    stock_anterior = insumo.stock_actual
                    insumo.stock_actual += cantidad_a_restaurar
                    insumo.save(update_fields=['stock_actual'])
                    movimientos.append(MovimientoInsumo(
                        insumo=insumo,
                        comanda=self,
                        tipo='REPOSICION',
                        cantidad=cantidad_a_restaurar,
                        stock_anterior=stock_anterior,
                        stock_posterior=insumo.stock_actual,
                        usuario=usuario,
                        observacion=f"Anulacion comanda #{self.id} - {linea.plato.nombre} x{linea.cantidad}"
                    ))
            MovimientoInsumo.objects.bulk_create(movimientos)
            self.estado = 'ANULADA'
            self.fecha_cierre = timezone.now()
            self.save(update_fields=['estado', 'fecha_cierre'])
            mesa = self.mesa
            union = UnionMesa.objects.filter(mesas=mesa, activa=True).first()
            mesas_a_liberar = [mesa]
            if union:
                mesas_a_liberar = list(union.mesas.all())
            for m in mesas_a_liberar:
                tiene_otra_comanda = self.__class__.objects.filter(
                    mesa=m, estado__in=['ABIERTA', 'EN_PREPARACION', 'LISTA']
                ).exclude(id=self.id).exists()
                if not tiene_otra_comanda:
                    tiene_reserva = m.reservas.filter(activa=True).exists()
                    if union:
                        tiene_reserva = tiene_reserva or union.reservas.filter(activa=True).exists()
                    m.estado = 'RESERVADA' if tiene_reserva else 'LIMPIEZA'
                    m.save(update_fields=['estado'])
        return self
    
    def pagar(self, metodo, monto, vuelto=0, referencia='', caja=None): 
        
        if self.estado not in ('ABIERTA', 'LISTA'):
            raise ValidationError('La comanda no esta lista para pagar')
        monto = Decimal(str(monto))
        if monto < self.total - Decimal('0.01'):
            raise ValidationError(
                f'El monto recibido ({monto}) es menor al total ({self.total})'
            )
        if metodo == 'TARJETA':
            if not referencia or len(referencia.strip()) < 4:
                raise ValidationError(
                    'Para pagos con tarjeta ingresa los últimos 4 dígitos de la tarjeta'
                )
            digitos = ''.join(c for c in referencia if c.isdigit())
            if len(digitos) < 4:
                raise ValidationError(
                    'La referencia debe contener al menos 4 dígitos de la tarjeta'
                )
        Pago.objects.create(
            comanda=self, metodo=metodo,
            monto=monto, vuelto=vuelto, referencia=referencia,
            caja=caja
        )
        self.estado = 'COBRADA'
        self.fecha_cierre = timezone.now()
        self.save()
        mesa = self.mesa
        union = UnionMesa.objects.filter(mesas=mesa, activa=True).first()
        tiene_reserva_mesa = mesa.reservas.filter(activa=True).exists()
        if union:
            tiene_reserva_mesa = tiene_reserva_mesa or union.reservas.filter(activa=True).exists()
            
        mesa.estado = 'RESERVADA' if tiene_reserva_mesa else 'LIMPIEZA'
        mesa.save(update_fields=['estado'])
        if union:
            for m in union.mesas.all():
                if m.id != mesa.id:
                    tiene_r = m.reservas.filter(activa=True).exists() or union.reservas.filter(activa=True).exists()
                    m.estado = 'RESERVADA' if tiene_r else 'LIMPIEZA'
                    m.save(update_fields=['estado'])
        return self
    def pagar_split(self, pagos_lista, caja=None):

        if self.estado not in ('ABIERTA', 'LISTA'):
            raise ValidationError('La comanda no esta lista para pagar')
        total_pagos = sum(p['monto'] for p in pagos_lista)
        if abs(total_pagos - self.total) > 0.01:
            raise ValidationError(
                f'Suma de pagos ({total_pagos}) no coincide con total ({self.total})'
            )
        for pd in pagos_lista:
            if pd.get('metodo') == 'TARJETA':
                ref = pd.get('referencia', '')
                if not ref or len(ref.strip()) < 4:
                    raise ValidationError(
                        'Para pagos con tarjeta ingresa los últimos 4 dígitos de la tarjeta'
                    )
                digitos = ''.join(c for c in ref if c.isdigit())
                if len(digitos) < 4:
                    raise ValidationError(
                        'La referencia debe contener al menos 4 dígitos de la tarjeta'
                    )
            Pago.objects.create(
                comanda=self, metodo=pd['metodo'],
                monto=pd['monto'], vuelto=pd.get('vuelto', 0),
                referencia=pd.get('referencia', ''),
                caja=caja
            )
        self.estado = 'COBRADA'
        self.fecha_cierre = timezone.now()
        self.save()
        mesa = self.mesa
        union = UnionMesa.objects.filter(mesas=mesa, activa=True).first()
        tiene_reserva_mesa = mesa.reservas.filter(activa=True).exists()
        if union:
            tiene_reserva_mesa = tiene_reserva_mesa or union.reservas.filter(activa=True).exists()
            
        mesa.estado = 'RESERVADA' if tiene_reserva_mesa else 'LIMPIEZA'
        mesa.save(update_fields=['estado'])
        if union:
            for m in union.mesas.all():
                if m.id != mesa.id:
                    tiene_r = m.reservas.filter(activa=True).exists() or union.reservas.filter(activa=True).exists()
                    m.estado = 'RESERVADA' if tiene_r else 'LIMPIEZA'
                    m.save(update_fields=['estado'])
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

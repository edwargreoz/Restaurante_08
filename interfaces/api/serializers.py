from decimal import Decimal
from rest_framework import serializers
from dominio.entidades.pago import Pago


class MesaSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    numero = serializers.IntegerField()
    capacidad = serializers.IntegerField()
    zona = serializers.CharField()
    estado = serializers.CharField()


class LineaComandaSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    plato = serializers.IntegerField(source='plato_id')
    nombre_plato = serializers.CharField(read_only=True)
    precio_unitario = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    cantidad = serializers.IntegerField()
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    observacion = serializers.CharField(read_only=True, default='')
    estado = serializers.CharField()


class ComandaSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    mesa = serializers.IntegerField(source='mesa_id')
    numero_mesa = serializers.IntegerField(read_only=True)
    mozo = serializers.IntegerField(source='mozo_id')
    nombre_mozo = serializers.CharField(read_only=True)
    estado = serializers.CharField()
    fecha_apertura = serializers.DateTimeField(read_only=True)
    fecha_cierre = serializers.DateTimeField(read_only=True)
    lineas = LineaComandaSerializer(many=True, read_only=True)
    total = serializers.DecimalField(max_digits=10, decimal_places=2)


class UnionMesaSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    mesas_ids = serializers.ListField(child=serializers.IntegerField(), source='mesa_ids')
    activo = serializers.BooleanField(required=False, default=True)
    capacidad_total = serializers.SerializerMethodField()

    def get_capacidad_total(self, obj):
        return getattr(obj, 'capacidad_total', lambda: 0)()


class CategoriaSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    nombre = serializers.CharField()
    es_bebida = serializers.BooleanField()
    orden_display = serializers.IntegerField()


class PlatoSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    nombre = serializers.CharField()
    descripcion = serializers.CharField(read_only=True, default='')
    precio = serializers.DecimalField(max_digits=10, decimal_places=2)
    categoria = serializers.IntegerField(source='categoria_id')
    categoria_nombre = serializers.CharField(read_only=True, default='')
    receta = serializers.IntegerField(source='receta_id', allow_null=True)
    receta_nombre = serializers.CharField(read_only=True, default='')
    tiempo_preparacion_min = serializers.IntegerField()
    disponible = serializers.BooleanField()
    imagen = serializers.CharField(read_only=True, default='')


class InsumoSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    nombre = serializers.CharField()
    unidad = serializers.CharField()
    stock_actual = serializers.DecimalField(max_digits=10, decimal_places=2)
    stock_minimo = serializers.DecimalField(max_digits=10, decimal_places=2)


class RecetaSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    nombre = serializers.CharField()


class RecetaInsumoSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    receta = serializers.IntegerField(source='receta_id')
    receta_nombre = serializers.CharField(read_only=True, default='')
    insumo = serializers.IntegerField(source='insumo_id')
    insumo_nombre = serializers.CharField(read_only=True, default='')
    insumo_unidad = serializers.CharField(read_only=True, default='')
    cantidad_por_porcion = serializers.DecimalField(max_digits=10, decimal_places=2)


class AgregarPlatoSerializer(serializers.Serializer):
    plato_id = serializers.IntegerField()
    cantidad = serializers.IntegerField(min_value=1, default=1)
    observacion = serializers.CharField(required=False, allow_blank=True, default='')


class AgregarPlatosRequestSerializer(serializers.Serializer):
    platos = AgregarPlatoSerializer(many=True, allow_empty=False)


class PagarRequestSerializer(serializers.Serializer):
    metodo = serializers.ChoiceField(choices=Pago.METODOS)
    monto = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal('0.01'))
    vuelto = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, default=0)
    referencia = serializers.CharField(required=False, allow_blank=True, default='')


class CocinaLineaSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    plato = serializers.IntegerField(source='plato_id')
    nombre_plato = serializers.CharField(read_only=True)
    cantidad = serializers.IntegerField()
    tiempo_prep = serializers.IntegerField(source='tiempo_preparacion_min', read_only=True)
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    observacion = serializers.CharField(read_only=True, default='')
    estado = serializers.CharField()


class CocinaComandaSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    numero_mesa = serializers.IntegerField(read_only=True)
    mozo_nombre = serializers.CharField(read_only=True)
    estado = serializers.CharField()
    fecha_apertura = serializers.DateTimeField(read_only=True)
    lineas = CocinaLineaSerializer(many=True, read_only=True)


class ReservaSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    mesa = serializers.IntegerField(source='mesa_id', allow_null=True)
    mesa_numero = serializers.IntegerField(read_only=True)
    union_mesa = serializers.IntegerField(source='union_mesa_id', allow_null=True)
    union_mesa_nombre = serializers.CharField(read_only=True)
    cliente_nombre = serializers.CharField()
    cliente_contacto = serializers.CharField(required=False, default='')
    fecha = serializers.DateField()
    hora_inicio = serializers.TimeField()
    hora_fin = serializers.TimeField()
    num_personas = serializers.IntegerField()
    observacion = serializers.CharField(required=False, default='')
    activo = serializers.BooleanField()
    creado_por = serializers.IntegerField(source='creado_por_id', read_only=True)
    creado_por_nombre = serializers.CharField(read_only=True)

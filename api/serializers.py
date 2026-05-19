from rest_framework import serializers
from mesas.models import Mesa, UnionMesa
from pedidos.models import Comanda, LineaComanda

class MesaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Mesa
        fields = '__all__'
class UnionMesaSerializer(serializers.ModelSerializer):
    """
    Serializer para UnionMesa.
    Incluye las mesas como campo anidado de solo lectura
    y expone capacidad_total como campo calculado.
    """
    mesas = MesaSerializer(
        many=True,
        read_only=True,
        source='mesas'
    )
    capacidad_total = serializers.SerializerMethodField()
    class Meta:
        model = UnionMesa
        fields = ['id', 'mesas', 'activa', 'fecha_creacion', 'capacidad_total']
    def get_capacidad_total(self, obj):
        return obj.capacidad_total()
class LineaComandaSerializer(serializers.ModelSerializer):
    """Cada linea de comanda tendra nombre y precio del plato para lectura mas facil."""
    nombre_plato = serializers.CharField(source='plato.nombre', read_only=True)
    precio_unitario = serializers.DecimalField(
        source='plato.precio',
        max_digits=10,
        decimal_places=2,
        read_only=True
    )
    subtotal = serializers.SerializerMethodField()
    class Meta:
        model = LineaComanda
        fields = [
            'id', 'plato', 'nombre_plato', 'precio_unitario',
            'cantidad', 'subtotal', 'observacion', 'estado'
        ]

    def get_subtotal(self, obj):
        return obj.cantidad * obj.plato.precio
    
class ComandaSerializer(serializers.ModelSerializer):
    """Incluye las lineas anidadas y calcula el total general."""
    lineas = LineaComandaSerializer(many=True, read_only=True)
    total = serializers.SerializerMethodField()
    numero_mesa = serializers.CharField(source='mesa.numero', read_only=True)
    nombre_mozo = serializers.CharField(source='mozo.get_full_name', read_only=True)
    class Meta:
        model = Comanda
        fields = [
            'id', 'mesa', 'numero_mesa', 'mozo',
            'nombre_mozo', 'estado', 'fecha_apertura',
            'fecha_cierre', 'lineas', 'total'
        ]
    def get_total(self, obj):
        return sum(
            linea.plato.precio * linea.cantidad
            for linea in obj.lineas.all()
        )

class AgregarPlatoSerializer(serializers.Serializer):
    plato_id= serializers.IntegerField()
    cantidad= serializers.IntegerField(min_value = 1 , default = 1)
    observacion = serializers.CharField(required=False, allow_blank=True, default='')

class AgregarPlatosRequestSerializer(serializers.Serializer):
    platos= AgregarPlatoSerializer(many= True,allow_empty= False)


from decimal import Decimal
from rest_framework import serializers
from mesas.models import Mesa, UnionMesa
from pedidos.models import Comanda, LineaComanda
from menu.models import Categoria, Plato
from inventario.models import Insumo, Receta, RecetaInsumo
from caja.models import Pago
from reservas.models import Reserva

class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = ['id', 'nombre', 'es_bebida', 'orden_display']

class PlatoSerializer(serializers.ModelSerializer):
    categoria_nombre = serializers.CharField(source='categoria.nombre', read_only=True)
    receta_nombre = serializers.CharField(source='receta.nombre', read_only=True)
    class Meta:
        model = Plato
        fields = ['id', 'nombre', 'descripcion', 'precio', 'categoria',
                  'categoria_nombre', 'receta', 'receta_nombre',
                  'tiempo_preparacion_min', 'disponible', 'imagen']

class InsumoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Insumo
        fields = ['id', 'nombre', 'unidad', 'stock_actual', 'stock_minimo']

class RecetaInsumoSerializer(serializers.ModelSerializer):
    receta_nombre = serializers.CharField(source='receta.nombre', read_only=True)
    insumo_nombre = serializers.CharField(source='insumo.nombre', read_only=True)
    insumo_unidad = serializers.CharField(source='insumo.unidad', read_only=True)
    class Meta:
        model = RecetaInsumo
        fields = ['id', 'receta', 'receta_nombre', 'insumo', 'insumo_nombre',
                  'insumo_unidad', 'cantidad_por_porcion']

class RecetaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Receta
        fields = ['id', 'nombre']

class MesaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Mesa
        fields = '__all__'

class UnionMesaSerializer(serializers.ModelSerializer):
    mesas = MesaSerializer(many=True, read_only=True)
    mesas_ids = serializers.PrimaryKeyRelatedField(
        many=True, write_only=True, queryset=Mesa.activos.all(), source='mesas'
    )
    capacidad_total = serializers.SerializerMethodField()
    class Meta:
        model = UnionMesa
        fields = ['id', 'mesas', 'mesas_ids', 'activo', 'creado_en', 'capacidad_total']
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
        return obj.subtotal
    
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
        return obj.total

class AgregarPlatoSerializer(serializers.Serializer):
    plato_id= serializers.IntegerField()
    cantidad= serializers.IntegerField(min_value = 1 , default = 1)
    observacion = serializers.CharField(required=False, allow_blank=True, default='')

class AgregarPlatosRequestSerializer(serializers.Serializer):
    platos= AgregarPlatoSerializer(many= True,allow_empty= False)

class PagarRequestSerializer(serializers.Serializer):
    metodo = serializers.ChoiceField(choices=Pago.METODOS)
    monto = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal('0.01'))
    vuelto = serializers.DecimalField(max_digits=10,decimal_places=2,required=False,default=0)
    referencia = serializers.CharField(required=False, allow_blank=True, default='')

class CocinaLineaSerializer(serializers.ModelSerializer):
    nombre_plato = serializers.CharField(source='plato.nombre', read_only=True)
    tiempo_prep = serializers.IntegerField(source = 'plato.tiempo_preparacion_min',read_only=True)
    subtotal= serializers.SerializerMethodField()

    class Meta:
        model = LineaComanda
        fields = ['id','plato','nombre_plato','cantidad','tiempo_prep','subtotal','observacion','estado']

    def get_subtotal(self,obj):
        return obj.cantidad * obj.plato.precio
    
class CocinaComandaSerializer(serializers.ModelSerializer):
    lineas = CocinaLineaSerializer(many=True, read_only=True)
    numero_mesa= serializers.CharField(source='mesa.numero', read_only= True)
    mozo_nombre= serializers.CharField(source ='mozo.get_full_name',read_only=True)

    class Meta:
        model = Comanda
        fields= ['id','numero_mesa','mozo_nombre','estado','fecha_apertura','lineas']

class ReservaSerializer(serializers.ModelSerializer):
    mesa_numero = serializers.IntegerField(source='mesa.numero', read_only=True)
    union_mesa_nombre = serializers.SerializerMethodField()
    creado_por_nombre = serializers.CharField(source='creado_por.get_full_name', read_only=True)
    class Meta:
        model = Reserva
        fields = ['id', 'mesa', 'mesa_numero', 'union_mesa', 'union_mesa_nombre',
                  'cliente_nombre', 'cliente_contacto',
                  'fecha', 'hora_inicio', 'hora_fin', 'num_personas',
                  'observacion', 'activo', 'creado_por', 'creado_por_nombre', 'creado_en']

    def get_union_mesa_nombre(self, obj):
        if obj.union_mesa:
            mesas = list(obj.union_mesa.mesas.values_list('numero', flat=True))
            return ' + '.join(f'Mesa {m}' for m in mesas)
        return None
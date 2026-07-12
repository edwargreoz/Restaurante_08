from django_filters import rest_framework as filters
from pedidos.models import Comanda
from menu.models import Plato
class ComandaFilter(filters.FilterSet):
    estado = filters.ChoiceFilter(choices=Comanda.ESTADOS)
    mesa = filters.NumberFilter(field_name='mesa__numero')
    mozo = filters.NumberFilter(field_name='mozo__id')
    fecha_desde = filters.DateFilter(field_name='fecha_apertura__date', lookup_expr='gte')
    fecha_hasta = filters.DateFilter(field_name='fecha_apertura__date', lookup_expr='lte')
    class Meta:
        model = Comanda
        fields = ['estado', 'mesa', 'mozo', 'fecha_desde', 'fecha_hasta']
class PlatoFilter(filters.FilterSet):
    categoria = filters.NumberFilter(field_name='categoria__id')
    disponible = filters.BooleanFilter()
    precio_min = filters.NumberFilter(field_name='precio', lookup_expr='gte')
    precio_max = filters.NumberFilter(field_name='precio', lookup_expr='lte')
    class Meta:
        model = Plato
        fields = ['categoria', 'disponible', 'precio_min', 'precio_max']

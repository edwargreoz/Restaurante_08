from django_filters import rest_framework as filters


COMANDA_ESTADOS = (
    ('ABIERTA', 'Abierta'),
    ('EN_PREPARACION', 'En Preparacion'),
    ('LISTA', 'Lista'),
    ('COBRADA', 'Cobrada'),
    ('ANULADA', 'Anulada'),
)


class ComandaFilter(filters.FilterSet):
    estado = filters.ChoiceFilter(choices=COMANDA_ESTADOS)
    mesa = filters.NumberFilter(field_name='numero_mesa')
    mozo = filters.NumberFilter(field_name='mozo_id')
    fecha_desde = filters.DateFilter(field_name='fecha_apertura__date', lookup_expr='gte')
    fecha_hasta = filters.DateFilter(field_name='fecha_apertura__date', lookup_expr='lte')

    class Meta:
        fields = ['estado', 'mesa', 'mozo', 'fecha_desde', 'fecha_hasta']


class PlatoFilter(filters.FilterSet):
    categoria = filters.NumberFilter(field_name='categoria_id')
    disponible = filters.BooleanFilter()
    precio_min = filters.NumberFilter(field_name='precio', lookup_expr='gte')
    precio_max = filters.NumberFilter(field_name='precio', lookup_expr='lte')

    class Meta:
        fields = ['categoria', 'disponible', 'precio_min', 'precio_max']

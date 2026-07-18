from django import template

register = template.Library()

@register.filter
def has_group(user, group_name):
    return user.is_superuser or user.groups.filter(name=group_name).exists()

ESTADO_DISPLAY = {
    'ABIERTA': 'Abierta',
    'EN_PREPARACION': 'En preparación',
    'LISTA': 'Lista',
    'COBRADA': 'Cobrada',
    'ANULADA': 'Anulada',
    'PENDIENTE': 'Pendiente',
    'EN_PREP': 'En preparación',
    'LISTO': 'Listo',
    'ENTREGADO': 'Entregado',
    'LIBRE': 'Libre',
    'OCUPADA': 'Ocupada',
    'RESERVADA': 'Reservada',
    'LIMPIEZA': 'Limpieza',
    'CERRADA': 'Cerrada',
}

ZONA_DISPLAY = {
    'SALON': 'Salón',
    'TERRAZA': 'Terraza',
    'VIP': 'VIP',
}

UNIDAD_DISPLAY = {
    'UNIDAD': 'Unidad',
    'KG': 'Kilogramo',
    'GR': 'Gramo',
    'LT': 'Litro',
    'ML': 'Mililitro',
}

@register.filter
def estado_display(value):
    return ESTADO_DISPLAY.get(value, value or '')

@register.filter
def zona_display(value):
    return ZONA_DISPLAY.get(value, value or '')

@register.filter
def unidad_display(value):
    return UNIDAD_DISPLAY.get(value, value or '')

METODO_DISPLAY = {
    'EFECTIVO': 'Efectivo',
    'TARJETA': 'Tarjeta',
    'YAPE': 'Yape',
    'PLIN': 'Plin',
    'TRANSFERENCIA': 'Transferencia',
}

@register.filter
def metodo_display(value):
    return METODO_DISPLAY.get(value, value or '')

@register.filter
def split_mesas(value):
    if not value:
        return []
    return [part.strip() for part in value.split(' + ') if part.strip()]

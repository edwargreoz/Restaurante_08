def es_mozo(user):
    return user.is_superuser or user.groups.filter(name='Mozo').exists()

def es_cocinero(user):
    return user.is_superuser or user.groups.filter(name='Cocinero').exists()

def es_cajero(user):
    return user.is_superuser or user.groups.filter(name='Cajero').exists()

def es_admin(user):
    return user.is_superuser

def es_mozo_o_cajero(user):
    return user.is_superuser or user.groups.filter(name__in=['Mozo', 'Cajero']).exists()

def es_mozo_o_cocinero(user):
    return user.is_superuser or user.groups.filter(name__in=['Mozo', 'Cocinero']).exists()

def es_cualquier_rol(user):
    return user.is_superuser or user.groups.filter(name__in=['Mozo', 'Cajero', 'Cocinero']).exists()

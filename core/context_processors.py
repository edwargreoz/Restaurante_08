from caja.models import Caja


def caja_context(request):
    if not request.user.is_authenticated:
        return {}
    try:
        caja_abierta = Caja.objects.filter(estado='ABIERTA').latest('fecha_apertura')
    except Caja.DoesNotExist:
        caja_abierta = None
    return {'caja_abierta_nav': caja_abierta}

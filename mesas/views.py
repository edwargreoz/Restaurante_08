

from django.shortcuts import render, get_object_or_404
from .models import Mesa


def plano_mesas(request):
    """
    Vista del plano del salon (plano_mesas.html).

    Obtiene todas las mesas y las pasa al template
    para renderizar un grid visual donde cada mesa
    se colorea segun su estado.

    Colores:
    - LIBRE (verde): disponible para asignar
    - OCUPADA (rojo): tiene una comanda activa
    - RESERVADA (amarillo): reservada para un cliente
    - LIMPIEZA (gris): en proceso de limpieza

    Al hacer clic en una mesa OCUPADA, abre la comanda activa.

    Sesion 03 - Consultas ORM: Mesa.objects.all()
    Sesion 04 - Render de templates con contextos.
    """
    mesas = Mesa.objects.all()

    context = {
        'mesas': mesas,
    }

    return render(request, 'mesas/plano_mesas.html', context)


def detalle_mesa(request, mesa_id):
    """
    Vista de detalle de una mesa.

    Muestra la informacion de la mesa y su comanda activa
    (si tiene una). Permite agregar platos a la comanda.

    Parametros:
    - mesa_id: ID de la mesa a consultar (desde la URL)

    get_object_or_404: retorna 404 si la mesa no existe.
    Sesion 03 - ORM: get_object_or_404 para busquedas seguras.
    Sesion 04 - Contextos en templates.

    Template: mesas/detalle_mesa.html
    """
    mesa = get_object_or_404(Mesa, id=mesa_id)

    context = {
        'mesa': mesa,
    }

    return render(request, 'mesas/detalle_mesa.html', context)

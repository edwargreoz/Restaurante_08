

from django.urls import path
from . import views

urlpatterns = [
    # Plano del salon: grid con todas las mesas coloreadas por estado
    # GET /mesas/ -> Vista general del salon
    path('mesas/', views.plano_mesas, name='plano_mesas'),

    # Detalle de una mesa especifica con su comanda activa
    # GET /mesas/5/ -> Detalle de la mesa con id=5
    path('mesas/<int:mesa_id>/', views.detalle_mesa, name='detalle_mesa'),
]

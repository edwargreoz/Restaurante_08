

from django.urls import path
from . import views

urlpatterns = [
    # Tomar Pedido
    path('pedidos/tomar/<int:mesa_id>/', views.tomar_pedido, name='tomar_pedido'),
    path('pedidos/agregar/<int:comanda_id>/', views.agregar_platos_pedido, name='agregar_platos_pedido'),
    # KDS Cocina
    path('cocina/', views.kds_panel, name='kds_panel'),
    path('cocina/enviar/<int:linea_id>/', views.enviar_cocina, name='enviar_cocina'),
    path('cocina/listo/<int:linea_id>/', views.marcar_listo, name='marcar_listo'),
]



from django.urls import path
from . import views

urlpatterns = [

    path('mesas/', views.plano_mesas, name='plano_mesas'),
    path('mesas/<int:mesa_id>/', views.detalle_mesa, name='detalle_mesa'),
    path('mesas/<int:mesa_id>/abrir/', views.abrir_comanda, name='abrir_comanda'),
    path('mesas/comanda/<int:comanda_id>/agregar/', views.agregar_plato_comanda, name='agregar_plato_comanda'),
    path('mesas/comanda/<int:comanda_id>/anular/', views.anular_comanda, name='anular_comanda'),
    # Unión de Mesas
    path('mesas/unir/', views.unir_mesas, name='unir_mesas'),
    path('mesas/deshacer-union/<int:union_id>/', views.deshacer_union, name='deshacer_union'),
    path('mesas/union/<int:union_id>/agregar/', views.agregar_mesa_union, name='agregar_mesa_union'),
    
]

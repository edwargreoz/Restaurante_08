

from django.urls import path
from . import views

urlpatterns = [
    path('inventario/', views.lista_insumos, name='lista_insumos'),
    path('inventario/gestion/', views.gestion_insumos, name='gestion_insumos'),
    path('inventario/crear/', views.crear_insumo, name='crear_insumo'),
    path('inventario/editar/<int:insumo_id>/', views.editar_insumo, name='editar_insumo'),
    path('inventario/eliminar/<int:insumo_id>/', views.eliminar_insumo, name='eliminar_insumo'),
]

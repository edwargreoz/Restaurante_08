

from django.urls import path
from . import views

urlpatterns = [
    # Catalogo de platos organizado por categoria
    path('menu/', views.catalogo_platos, name='catalogo_platos'),
    path('menu/gestion/', views.gestion_menu, name='gestion_menu'),
    path('menu/crear-categoria/', views.crear_categoria, name='crear_categoria'),
    path('menu/crear-plato/', views.crear_plato, name='crear_plato'),
    path('menu/editar/<int:plato_id>/', views.editar_plato, name='editar_plato'),
    path('menu/eliminar/<int:plato_id>/', views.eliminar_plato, name='eliminar_plato'),
    
]

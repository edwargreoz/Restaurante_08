

from django.urls import path
from . import views

urlpatterns = [
    path('inventario/', views.lista_insumos, name='lista_insumos'),
    path('inventario/gestion/', views.gestion_insumos, name='gestion_insumos'),
    path('inventario/crear/', views.crear_insumo, name='crear_insumo'),
    path('inventario/editar/<int:insumo_id>/', views.editar_insumo, name='editar_insumo'),
    path('inventario/eliminar/<int:insumo_id>/', views.eliminar_insumo, name='eliminar_insumo'),
    path('inventario/presentaciones/<int:insumo_id>/', views.presentaciones_insumo, name='presentaciones_insumo'),
    path('inventario/presentaciones/eliminar/<int:presentacion_id>/', views.eliminar_presentacion, name='eliminar_presentacion'),
    path('inventario/presentaciones/compra/<int:presentacion_id>/', views.registrar_compra_presentacion, name='registrar_compra_presentacion'),
    path('inventario/unidades-cocina/', views.unidades_cocina, name='unidades_cocina'),
    path('inventario/unidades-cocina/eliminar/<int:unidad_id>/', views.eliminar_unidad_cocina, name='eliminar_unidad_cocina'),
    path('inventario/catalogo-presentaciones/', views.catalogo_presentaciones, name='catalogo_presentaciones'),
    path('inventario/catalogo-presentaciones/eliminar/<int:presentacion_id>/', views.eliminar_presentacion_catalogo, name='eliminar_presentacion_catalogo'),
    path('recetas/', views.lista_recetas, name='lista_recetas'),
    path('recetas/crear/', views.crear_receta, name='crear_receta'),
    path('recetas/editar/<int:receta_id>/', views.editar_receta, name='editar_receta'),
    path('recetas/eliminar-insumo/<int:receta_insumo_id>/', views.eliminar_receta, name='eliminar_receta'),
    path('recetas/eliminar/<int:receta_id>/', views.eliminar_receta_completa, name='eliminar_receta_completa'),
]

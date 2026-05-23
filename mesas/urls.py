

from django.urls import path
from . import views

urlpatterns = [

    path('mesas/', views.plano_mesas, name='plano_mesas'),
    path('mesas/<int:mesa_id>/', views.detalle_mesa, name='detalle_mesa'),
    path('mesas/<int:mesa_id>/abrir/', views.abrir_comanda, name='abrir_comanda'),
    path('mesas/comanda/<int:comanda_id>/agregar/', views.agregar_plato_comanda, name='agregar_plato_comanda'),
    path('mesas/comanda/<int:comanda_id>/anular/', views.anular_comanda, name='anular_comanda'),
    # Unión de Mesas
    path('mesas/limpieza-a-libre/<int:mesa_id>/', views.marcar_mesa_libre, name='marcar_mesa_libre'),
    path('mesas/unir/', views.unir_mesas, name='unir_mesas'),
    path('mesas/deshacer-union/<int:union_id>/', views.deshacer_union, name='deshacer_union'),
    path('mesas/union/<int:union_id>/agregar/', views.agregar_mesa_union, name='agregar_mesa_union'),
    
    # ----------------- ADMINISTRADOR (CRUD MESAS) -----------------
    path('mesas/admin/', views.lista_mesas_admin, name='lista_mesas_admin'),
    path('mesas/admin/crear/', views.crear_mesa, name='crear_mesa'),
    path('mesas/admin/<int:mesa_id>/editar/', views.editar_mesa, name='editar_mesa'),
    path('mesas/admin/<int:mesa_id>/eliminar/', views.eliminar_mesa, name='eliminar_mesa'),
]

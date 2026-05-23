

from django.urls import path
from . import views

urlpatterns = [
    # Pagina de inicio - redirige al login
    path('', views.login_view, name='home'),

    # Inicio de sesion (GET: formulario, POST: autenticar)
    path('login/', views.login_view, name='login'),

    # Cerrar sesion
    path('logout/', views.logout_view, name='logout'),

    # Dashboard principal (requiere autenticacion)
    path('dashboard/', views.dashboard_view, name='dashboard'),

    # Gestion de usuarios (CRUD)
    path('usuarios/', views.lista_usuarios, name='lista_usuarios'),
    path('usuarios/crear/', views.crear_usuario, name='crear_usuario'),
    path('usuarios/editar/<int:user_id>/', views.editar_usuario, name='editar_usuario'),
    path('usuarios/eliminar/<int:user_id>/', views.eliminar_usuario, name='eliminar_usuario'),
]

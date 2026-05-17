

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
]

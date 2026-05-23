

from django.urls import path
from . import views

urlpatterns = [
    path('caja/cobrar/<int:comanda_id>/', views.cobrar_comanda, name='cobrar_comanda'),
    path('caja/comandas/', views.lista_comandas_cobro, name='lista_comandas_cobro'),
    path('caja/apertura/', views.apertura_turno, name='apertura_turno'),
    path('reportes/', views.reportes_turno, name='reportes_turno'),
]

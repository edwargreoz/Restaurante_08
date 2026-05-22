

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Admin de Django
    path('admin/', admin.site.urls),
    # Vistas web del core (login, dashboard)
    path('', include('core.urls')),
    # Vistas web de mesas (plano del salon)
    path('', include('mesas.urls')),
    # API REST versionada 
    path('api/v1/', include('api.urls')),
    # Vistas web de menu (catalogo, gestion)
    path('', include('menu.urls')),
    # Vistas web de pedidos (tomar pedido, KDS)
    path('', include('pedidos.urls')),
    # Vistas web de inventario (lista, CRUD insumos)
    path('', include('inventario.urls')),
    # Vistas web de caja (cobrar, turno, reportes)
    path('', include('caja.urls')),
    # Vistas web de reservas
    path('', include('reservas.urls')),
]

# Servir archivos media en modo desarrollo
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

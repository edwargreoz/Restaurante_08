

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Admin de Django (Sesion 04 - Componentes Django)
    path('admin/', admin.site.urls),

    # Vistas web del core (login, dashboard)
    path('', include('core.urls')),

    # Vistas web de mesas (plano del salon)
    path('', include('mesas.urls')),

    # API REST versionada (Sesion 05 y 06)
    path('api/v1/', include('api.urls')),
]

# Servir archivos media en modo desarrollo
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

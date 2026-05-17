

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from .views import MesaViewSet

# Router principal para ViewSets
# Los ViewSets se registran con: router.register('nombre', ViewSet)
router = DefaultRouter()
router.register(r'mesas', MesaViewSet)

urlpatterns = [
    # Autenticacion JWT (Sesion 06)
    # POST /api/v1/auth/token/  -> {username, password} -> {access, refresh}
    path('auth/token/',TokenObtainPairView.as_view(),name='token_obtain'),

    # POST /api/v1/auth/token/refresh/ -> {refresh} -> {access}
    path( 'auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh' ),

    # Router con ViewSets registrados
    path('', include(router.urls)),
]

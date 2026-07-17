

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from .views import (
    MesaViewSet, UnionMesaViewSet, ComandaViewSet, LineaComandaViewSet,
    CocinaViewSet, ReportesViewSet, CategoriaViewSet, PlatoViewSet,
    InsumoViewSet, RecetaViewSet, RecetaInsumoViewSet, ReservaViewSet,
)
# Router principal para ViewSets
# Los ViewSets se registran con: router.register('nombre', ViewSet)
router = DefaultRouter()
router.register(r'mesas', MesaViewSet, basename='mesa')
router.register(r'uniones-mesas',UnionMesaViewSet, basename='unionmesa')
router.register(r'comandas',ComandaViewSet, basename='comanda')
router.register(r'lineas-comanda',LineaComandaViewSet, basename='lineacomanda')
router.register(r'cocina', CocinaViewSet, basename='cocina')
router.register(r'reportes',ReportesViewSet,basename='reportes')
router.register(r'categorias', CategoriaViewSet, basename='categoria')
router.register(r'platos', PlatoViewSet, basename='plato')
router.register(r'insumos', InsumoViewSet, basename='insumo')
router.register(r'recetas', RecetaViewSet, basename='receta')
router.register(r'recetas-insumo', RecetaInsumoViewSet, basename='recetainsumo')
router.register(r'reservas', ReservaViewSet, basename='reserva')


urlpatterns = [
    # Autenticacion JWT 
    # POST /api/v1/auth/token/  -> {username, password} -> {access, refresh}
    path('auth/token/',TokenObtainPairView.as_view(),name='token_obtain'),

    # POST /api/v1/auth/token/refresh/ -> {refresh} -> {access}
    path( 'auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh' ),

    # Router con ViewSets registrados
    path('', include(router.urls)),
]

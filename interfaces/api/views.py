from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response


from core.excepciones import AppError
from infraestructura.container import get_container

    
from .filters import ComandaFilter, PlatoFilter
from .serializers import (
    MesaSerializer, UnionMesaSerializer, ComandaSerializer,
    AgregarPlatosRequestSerializer, PagarRequestSerializer,
    LineaComandaSerializer, CocinaComandaSerializer,
    CategoriaSerializer, PlatoSerializer,
    InsumoSerializer, RecetaSerializer, RecetaInsumoSerializer,
    ReservaSerializer,
)
from .permissions import EsMozo, EsCocinero, EsCajero, EsAdmin


class CategoriaViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet de solo lectura para consultar categorías del menú."""
    permission_classes = [EsMozo | EsAdmin]
    def get_queryset(self):
        return get_container().categoria_service.categoria_repo.listar_con_platos()
    serializer_class = CategoriaSerializer

class PlatoViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet de solo lectura para consultar platos del menú con su precio y disponibilidad."""
    permission_classes = [EsMozo | EsAdmin]
    def get_queryset(self):
        return get_container().plato_service.plato_repo.listar()
    serializer_class = PlatoSerializer
    filterset_class = PlatoFilter

class InsumoViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet de solo lectura para consultar insumos del inventario (solo admin)."""
    permission_classes = [EsAdmin]
    def get_queryset(self):
        return get_container().insumo_service.repo.listar()
    serializer_class = InsumoSerializer

class RecetaViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet de solo lectura para consultar recetas asociadas a platos."""
    permission_classes = [EsAdmin]
    def get_queryset(self):
        return get_container().receta_service.listar_recetas()
    serializer_class = RecetaSerializer

class RecetaInsumoViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet de solo lectura para consultar los ingredientes de cada receta."""
    permission_classes = [EsAdmin]
    def get_queryset(self):
        return get_container().receta_service.listar_receta_insumos()
    serializer_class = RecetaInsumoSerializer

class ReservaViewSet(viewsets.ModelViewSet):
    """ViewSet para gestionar reservas. Soporta crear, editar, cancelar y finalizar."""
    permission_classes = [EsMozo | EsAdmin]
    def get_queryset(self):
        return get_container().reserva_service.listar()
    serializer_class = ReservaSerializer

    def perform_destroy(self, instance):
        container = get_container()
        container.reserva_service.cancelar(instance.id)

class MesaViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet de solo lectura para consultar mesas y su estado actual en tiempo real."""
    permission_classes = [EsMozo | EsAdmin]
    def get_queryset(self):
        return get_container().mesa_service.mesa_repo.listar_activas()
    serializer_class = MesaSerializer

    @action(detail=False, methods=['get'])
    def estado_actual(self, request):
        """
        GET /api/v1/mesas/estado-actual/
        Retorna todas las mesas con su estado.
        """
        mesas = self.get_queryset()
        serializer = self.get_serializer(mesas, many=True)
        return Response(serializer.data)
    

class UnionMesaViewSet(viewsets.ModelViewSet):
    """ViewSet para gestionar uniones de mesas (mesas combinadas)."""
    permission_classes = [EsMozo | EsAdmin]
    def get_queryset(self):
        return get_container().union_mesa_service.listar()
    serializer_class = UnionMesaSerializer

class ComandaViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar comandas del restaurante.
    Incluye acciones para abrir, agregar platos, anular, pagar y pagar con split.
    """
    permission_classes = [EsMozo | EsCajero|EsAdmin]
    def get_queryset(self):
        return get_container().comanda_service.comanda_repo.listar()
    serializer_class = ComandaSerializer
    filterset_class = ComandaFilter

    @action(detail=False,methods=['post'])
    def abrir(self,request):
        """
        POST /api/v1/comandas/abrir/
        Crea una comanda nueva en una mesa.
        Body: {"mesa_id": 1}
        """
        mesa_id = request.data.get('mesa_id')
        if not mesa_id:
            return Response(
                {'error' : 'mesa_id es obligatorio'},
                status= status.HTTP_400_BAD_REQUEST)
        try:
            container = get_container()
            comanda = container.comanda_service.abrir(mesa_id, request.user)
        except AppError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        comanda.refresh_from_db()
        serializer = self.get_serializer(comanda)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['POST'])
    def agregar_platos(self,request,pk=None):
        """
        POST /api/v1/comandas/{id}/platos/
        Agrega platos a una comanda verificando stock de insumos.
        Body: {"platos": [{"plato_id": 1, "cantidad": 2, "observacion": "sin sal"}]}
        """ 
        comanda = self.get_object()
        
        serializer = AgregarPlatosRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            container = get_container()
            container.comanda_service.agregar_platos(comanda.id, serializer.validated_data['platos'], usuario=request.user)
        except AppError as e:
            if hasattr(e, 'args') and e.args and isinstance(e.args[0], dict):
                error_data = e.args[0]
            else:
                error_data = {'error': str(e)}
            return Response(
                error_data,
                status=status.HTTP_400_BAD_REQUEST
            )
        comanda.refresh_from_db()
        serializer = self.get_serializer(comanda)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def anular(self, request, pk=None):
        """
        POST /api/v1/comandas/{id}/anular/
        Anula una comanda y restaura el stock de insumos.
        """
        comanda = self.get_object()
        try:
            container = get_container()
            container.comanda_service.anular(comanda.id, usuario=request.user)
        except AppError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        comanda.refresh_from_db()
        serializer = self.get_serializer(comanda)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def pagar(self,request, pk=None):
        """
        POST /api/v1/comandas/{id}/pagar/
        Registra el pago de una comanda. La comanda debe estar en estado LISTA.
        Body: {"metodo": "EFECTIVO", "monto": 50.00, "vuelto": 0}
        """
        comanda = self.get_object()
        serializer = PagarRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data

        try:
            container = get_container()
            caja = container.caja_service.obtener_activa()
            container.comanda_service.pagar(
                comanda.id,
                metodo=data['metodo'], monto=data['monto'],
                vuelto=data.get('vuelto', 0),
                referencia=data.get('referencia', ''),
                caja=caja,
            )
        except AppError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        comanda.refresh_from_db()
        serializer = self.get_serializer(comanda)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def pagar_split(self, request, pk=None):
        """
        POST /api/v1/comandas/{id}/pagar-split/
        Registra múltiples pagos para una comanda (pago dividido).
        Body: {"pagos": [{"metodo": "EFECTIVO", "monto": 25.00}, {"metodo": "TARJETA", "monto": 25.00, "referencia": "1234"}]}
        """
        comanda = self.get_object()
        pagos_data = request.data.get('pagos', [])
        if not pagos_data:
            return Response(
                {'error': 'Debe enviar al menos un pago'},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            container = get_container()
            caja = container.caja_service.obtener_activa()
            container.comanda_service.pagar_split(comanda.id, pagos_data, caja=caja)
        except AppError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        comanda.refresh_from_db()
        serializer = self.get_serializer(comanda)
        return Response(serializer.data, status=status.HTTP_200_OK)

class LineaComandaViewSet(viewsets.ModelViewSet):
    """ViewSet para gestionar líneas de comanda (platos individuales). Permite enviar a cocina y marcar como listo."""
    permission_classes = [EsCocinero | EsAdmin]
    def get_queryset(self):
        return get_container().linea_comanda_service.linea_comanda_repo.listar()
    serializer_class = LineaComandaSerializer
    filterset_fields= ['estado','comanda','plato']
    search_fields = ['plato__nombre','observacion']

    @action(detail=True, methods=['post'])
    def enviar_cocina (self, request, pk=None):
        """
        POST /api/v1/lineas-comanda/{id}/enviar-cocina/
        Envía una línea de comanda a preparación en cocina.
        """
        linea = self.get_object()
        try:
            container = get_container()
            container.linea_comanda_service.enviar_cocina(linea.id)
        except AppError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
                )
        linea.refresh_from_db()
        serializer = self.get_serializer(linea)
        return Response(serializer.data)
    
    @action(detail=True, methods=['patch'])
    def marcar_listo(self,request,pk=None):
        """
        PATCH /api/v1/lineas-comanda/{id}/marcar-listo/
        Marca una línea de comanda como lista para entregar.
        """
        linea = self.get_object()
        try:
            container = get_container()
            container.linea_comanda_service.marcar_listo(linea.id)
        except AppError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
                )
        linea.refresh_from_db()
        serializer = self.get_serializer(linea)
        return Response(serializer.data)

class CocinaViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet de solo lectura para el panel de cocina (KDS). Muestra comandas en preparación con sus líneas."""
    permission_classes = [EsCocinero | EsAdmin]
    serializer_class = CocinaComandaSerializer

    def get_queryset(self):
        return get_container().comanda_service.comanda_repo.listar_para_kds()
    
class ReportesViewSet(viewsets.ViewSet):
    """ViewSet para consultar reportes de ventas del turno y stock crítico de insumos."""
    permission_classes = [EsCajero|EsAdmin]

    @action(detail=False,methods=['get'])
    def ventas_turno(self, request):
        """
        GET /api/v1/reportes/ventas-turno/
        Retorna el resumen de ventas del turno. Params: caja_id, fecha_desde, fecha_hasta.
        """
        container = get_container()
        data = container.pago_service.reporte_ventas(
            caja_id=request.query_params.get('caja_id'),
            fecha_desde=request.query_params.get('fecha_desde'),
            fecha_hasta=request.query_params.get('fecha_hasta'),
        )
        return Response(data)

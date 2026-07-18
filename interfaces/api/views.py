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
    """ViewSet de solo lectura para consultar categorias del menu."""
    permission_classes = [EsMozo | EsAdmin]
    serializer_class = CategoriaSerializer

    def get_queryset(self):
        return get_container().categoria_service.listar_categorias()


class PlatoViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet de solo lectura para consultar platos del menu con su precio y disponibilidad."""
    permission_classes = [EsMozo | EsAdmin]
    serializer_class = PlatoSerializer
    filterset_class = PlatoFilter

    def get_queryset(self):
        return get_container().plato_service.listar()


class InsumoViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet de solo lectura para consultar insumos del inventario (solo admin)."""
    permission_classes = [EsAdmin]
    serializer_class = InsumoSerializer

    def get_queryset(self):
        return get_container().insumo_service.listar_insumos()


class RecetaViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet de solo lectura para consultar recetas asociadas a platos."""
    permission_classes = [EsAdmin]
    serializer_class = RecetaSerializer

    def get_queryset(self):
        return get_container().receta_service.listar_recetas()


class RecetaInsumoViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet de solo lectura para consultar los ingredientes de cada receta."""
    permission_classes = [EsAdmin]
    serializer_class = RecetaInsumoSerializer

    def get_queryset(self):
        return get_container().receta_service.listar_receta_insumos()


class ReservaViewSet(viewsets.ModelViewSet):
    """ViewSet para gestionar reservas. Soporta crear, editar, cancelar y finalizar."""
    permission_classes = [EsMozo | EsAdmin]
    serializer_class = ReservaSerializer

    def get_queryset(self):
        return get_container().reserva_service.listar()

    def perform_destroy(self, instance):
        container = get_container()
        container.reserva_service.cancelar(instance.id)


class MesaViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet de solo lectura para consultar mesas y su estado actual en tiempo real."""
    permission_classes = [EsMozo | EsAdmin]
    serializer_class = MesaSerializer

    def get_queryset(self):
        return get_container().mesa_service.listar_activas()

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
    serializer_class = UnionMesaSerializer

    def get_queryset(self):
        return get_container().union_mesa_service.listar()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        mesas_ids = serializer.validated_data.get('mesa_ids', [])
        try:
            container = get_container()
            union = container.union_mesa_service.crear(mesas_ids, comanda_service=container.comanda_service)
        except AppError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
            
        resp_serializer = self.get_serializer(union)
        return Response(resp_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='agregar-mesa')
    def agregar_mesa(self, request, pk=None):
        union_id = int(pk) if pk else None
        mesa_id = request.data.get('mesa_id')
        if not mesa_id:
            return Response({'error': 'mesa_id es obligatorio'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            container = get_container()
            union = container.union_mesa_service.agregar_mesa(
                union_id, mesa_id, request.user,
                comanda_service=container.comanda_service,
                caja_service=container.caja_service
            )
        except AppError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = self.get_serializer(union)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ComandaViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar comandas del restaurante.
    Incluye acciones para abrir, agregar platos, anular, pagar y pagar con split.
    """
    permission_classes = [EsMozo | EsCajero | EsAdmin]
    serializer_class = ComandaSerializer
    filterset_class = ComandaFilter

    def get_queryset(self):
        return get_container().comanda_service.listar()

    @action(detail=False, methods=['post'])
    def abrir(self, request):
        """
        POST /api/v1/comandas/abrir/
        Crea una comanda nueva en una mesa.
        Body: {"mesa_id": 1}
        """
        mesa_id = request.data.get('mesa_id')
        if not mesa_id:
            return Response(
                {'error': 'mesa_id es obligatorio'},
                status=status.HTTP_400_BAD_REQUEST)
        try:
            container = get_container()
            comanda = container.comanda_service.abrir(mesa_id, request.user)
        except AppError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        comanda = container.comanda_service.obtener_por_id(comanda.id) if comanda.id else comanda
        serializer = self.get_serializer(comanda)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['POST'])
    def agregar_platos(self, request, pk=None):
        """
        POST /api/v1/comandas/{id}/platos/
        Agrega platos a una comanda verificando stock de insumos.
        Body: {"platos": [{"plato_id": 1, "cantidad": 2, "observacion": "sin sal"}]}
        """
        comanda_id = int(pk) if pk else None

        serializer = AgregarPlatosRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            container = get_container()
            container.comanda_service.agregar_platos(comanda_id, serializer.validated_data['platos'], usuario=request.user)
        except AppError as e:
            if hasattr(e, 'args') and e.args and isinstance(e.args[0], dict):
                error_data = e.args[0]
            else:
                error_data = {'error': str(e)}
            return Response(
                error_data,
                status=status.HTTP_400_BAD_REQUEST
            )
        comanda = container.comanda_service.obtener_por_id(comanda_id) if comanda_id else None
        serializer = self.get_serializer(comanda)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def anular(self, request, pk=None):
        """
        POST /api/v1/comandas/{id}/anular/
        Anula una comanda y restaura el stock de insumos.
        """
        comanda_id = int(pk) if pk else None
        try:
            container = get_container()
            container.comanda_service.anular(comanda_id, usuario=request.user)
        except AppError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        comanda = container.comanda_service.obtener_por_id(comanda_id) if comanda_id else None
        serializer = self.get_serializer(comanda)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def pagar(self, request, pk=None):
        """
        POST /api/v1/comandas/{id}/pagar/
        Registra el pago de una comanda. La comanda debe estar en estado LISTA.
        Body: {"metodo": "EFECTIVO", "monto": 50.00, "vuelto": 0}
        """
        comanda_id = int(pk) if pk else None
        serializer = PagarRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data

        try:
            container = get_container()
            caja = container.caja_service.obtener_activa()
            container.comanda_service.pagar(
                comanda_id,
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
        comanda = container.comanda_service.obtener_por_id(comanda_id) if comanda_id else None
        serializer = self.get_serializer(comanda)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def pagar_split(self, request, pk=None):
        """
        POST /api/v1/comandas/{id}/pagar-split/
        Registra multiples pagos para una comanda (pago dividido).
        Body: {"pagos": [{"metodo": "EFECTIVO", "monto": 25.00}, {"metodo": "TARJETA", "monto": 25.00, "referencia": "1234"}]}
        """
        comanda_id = int(pk) if pk else None
        pagos_data = request.data.get('pagos', [])
        if not pagos_data:
            return Response(
                {'error': 'Debe enviar al menos un pago'},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            container = get_container()
            caja = container.caja_service.obtener_activa()
            container.comanda_service.pagar_split(comanda_id, pagos_data, caja=caja)
        except AppError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        comanda = container.comanda_service.obtener_por_id(comanda_id) if comanda_id else None
        serializer = self.get_serializer(comanda)
        return Response(serializer.data, status=status.HTTP_200_OK)


class LineaComandaViewSet(viewsets.ModelViewSet):
    """ViewSet para gestionar lineas de comanda (platos individuales). Permite enviar a cocina y marcar como listo."""
    permission_classes = [EsCocinero | EsAdmin]
    serializer_class = LineaComandaSerializer
    filterset_fields = ['estado', 'comanda', 'plato']
    search_fields = ['plato__nombre', 'observacion']

    def get_queryset(self):
        return get_container().linea_comanda_service.listar()

    @action(detail=True, methods=['post'])
    def enviar_cocina(self, request, pk=None):
        """
        POST /api/v1/lineas-comanda/{id}/enviar-cocina/
        Envía una linea de comanda a preparacion en cocina.
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
        linea = container.linea_comanda_service.obtener_por_id(linea.id) if linea.id else linea
        serializer = self.get_serializer(linea)
        return Response(serializer.data)

    @action(detail=True, methods=['patch'])
    def marcar_listo(self, request, pk=None):
        """
        PATCH /api/v1/lineas-comanda/{id}/marcar-listo/
        Marca una linea de comanda como lista para entregar.
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
        linea = container.linea_comanda_service.obtener_por_id(linea.id) if linea.id else linea
        serializer = self.get_serializer(linea)
        return Response(serializer.data)


class CocinaViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet de solo lectura para el panel de cocina (KDS). Muestra comandas en preparacion con sus lineas."""
    permission_classes = [EsCocinero | EsAdmin]
    serializer_class = CocinaComandaSerializer

    def get_queryset(self):
        return get_container().comanda_service.listar_para_kds()


class ReportesViewSet(viewsets.ViewSet):
    """ViewSet para consultar reportes de ventas del turno y stock critico de insumos."""
    permission_classes = [EsCajero | EsAdmin]

    @action(detail=False, methods=['get'])
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

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from django.db.models import Q
from django.core.exceptions import ValidationError

from mesas.models import Mesa, UnionMesa
from pedidos.models import Comanda, LineaComanda
from caja.models import Pago
    
from .filters import ComandaFilter
from .serializers import (
    MesaSerializer, UnionMesaSerializer, ComandaSerializer,
    AgregarPlatosRequestSerializer, PagarRequestSerializer,
    LineaComandaSerializer, CocinaComandaSerializer
)
from .permissions import EsMozo, EsCocinero, EsCajero, EsAdmin


class MesaViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet de solo lectura para Mesas.
    ReadOnlyModelViewSet: solo GET (list + retrieve),
    no permite crear, editar ni eliminar desde la API.
    """
    permission_classes = [EsMozo | EsAdmin]
    queryset = Mesa.objects.all()
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
    """Crud completo para el tema de union de mesas
    Aqui vamos a crear, leer , actualizar y elimanr uniones"""
    permission_classes = [EsMozo | EsAdmin]
    queryset = UnionMesa.objects.all()
    serializer_class = UnionMesaSerializer

class ComandaViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar comandas.
    Incluye @action abrir para crear comandas nuevas.
    """
    permission_classes = [EsMozo | EsCajero|EsAdmin]
    queryset = Comanda.objects.prefetch_related('lineas__plato')
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
        with transaction.atomic():
            mesa = Mesa.objects.select_for_update().filter(id=mesa_id).first()
            if not mesa:
                return Response(
                    {'error':'Mesa no encontrada'},
                    status= status.HTTP_404_NOT_FOUND)
        
            try:
                comanda = Comanda.abrir(mesa_id, request.user)
            except ValidationError as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
        serializer = self.get_serializer(comanda)
        return Response(serializer.data , status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['POST'])
    def agregar_platos(self,request,pk=None):
        """
        POST /api/v1/comandas/{id}/platos/
        Body: {"platos": [{"plato_id": 1, "cantidad": 2, "observacion": "sin sal"}, ...]}
        Agrega platos a una comanda verificando stock de insumos.
        """ 
        comanda = self.get_object()
        
        serializer = AgregarPlatosRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            comanda.agregar_platos(serializer.validated_data['platos'])
        except ValidationError as e:
            return Response(
                e.message_dict if hasattr(e, 'message_dict')
                else {'error':str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        serializer = self.get_serializer(comanda)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def pagar(self,request, pk=None):
        comanda = self.get_object()
        if comanda.estado not in ('ABIERTA','LISTA'):
            return Response(
                {'error': 'La comanda no esta lista para pagar'},
                status=status.HTTP_400_BAD_REQUEST
            )
        serializer = PagarRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data

        with transaction.atomic():
            comanda = Comanda.objects.select_for_update().get(id=comanda.id)
            try:
                comanda.pagar(
                    metodo=data['metodo'],monto=data['monto'],
                    vuelto = data.get('vuelto',0),
                    referencia= data.get('referencia','')    
                )
            except ValidationError as e:
                return Response(
                    {'error' :  str(e)},
                    status=status.HTTP_400_BAD_REQUEST 
                )
        serializer = self.get_serializer(comanda)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def pagar_split(self, request, pk=None):
        comanda = self.get_object()
        if comanda.estado not in ('ABIERTA', 'LISTA'):
            return Response(
                {'error': 'La comanda no esta lista para pagar'},
                status=status.HTTP_400_BAD_REQUEST
            )
        pagos_data = request.data.get('pagos', [])
        if not pagos_data:
            return Response(
                {'error': 'Debe enviar al menos un pago'},
                status=status.HTTP_400_BAD_REQUEST
            )
        with transaction.atomic():
            comanda = Comanda.objects.select_for_update().get(id=comanda.id)
            try:
                comanda.pagar_split(pagos_data)
            except ValidationError as e:
                return Response(
                    e.message_dict if hasattr(e, 'message_dict')
                    else {'error': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
        serializer = self.get_serializer(comanda)
        return Response(serializer.data, status=status.HTTP_200_OK)

class LineaComandaViewSet(viewsets.ModelViewSet):
    permission_classes = [EsCocinero | EsAdmin]
    queryset = LineaComanda.objects.select_related('plato','comanda__mesa')
    serializer_class = LineaComandaSerializer
    filterset_fields= ['estado','comanda','plato']
    search_fields = ['plato__nombre','observacion']

    @action(detail=True, methods=['post'])
    def enviar_cocina (self, request, pk=None):
        linea = self.get_object()
        try:
            linea.enviar_cocina()
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
                )
        serializer = self.get_serializer(linea)
        return Response(serializer.data)
    
    @action(detail=True, methods=['patch'])
    def marcar_listo(self,request,pk=None):
        linea = self.get_object()
        try:
            linea.marcar_listo()
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
                )
        serializer = self.get_serializer(linea)
        return Response(serializer.data)

class CocinaViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Comanda.objects.filter(
        Q(estado='EN_PREPARACION') | Q(lineas__estado__in=['PENDIENTE', 'EN_PREP'])
    ).prefetch_related('lineas__plato').distinct().order_by('fecha_apertura')
    permission_classes = [EsCocinero | EsAdmin]
    serializer_class = CocinaComandaSerializer

class ReportesViewSet(viewsets.ViewSet):
    permission_classes = [EsCajero|EsAdmin]

    @action(detail=False,methods=['get'])
    def ventas_turno(self, request):
        data = Pago.objects.reporte_ventas(
            caja_id=request.query_params.get('caja_id'),
            fecha_desde=request.query_params.get('fecha_desde'),
            fecha_hasta=request.query_params.get('fecha_hasta'),
        )
        return Response(data)


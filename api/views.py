
from rest_framework import viewsets, generics, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from mesas.models import Mesa , UnionMesa
from .serializers import MesaSerializer , UnionMesaSerializer,ComandaSerializer
from pedidos.models import Comanda


class MesaViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet de solo lectura para Mesas.
    ReadOnlyModelViewSet: solo GET (list + retrieve),
    no permite crear, editar ni eliminar desde la API.
    """
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
    queryset = UnionMesa.objects.all()
    serializer_class = UnionMesaSerializer

class ComandaViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar comandas.
    Incluye @action abrir para crear comandas nuevas.
    """
    queryset = Comanda.objects.all()
    serializer_class = ComandaSerializer

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
                 status= status.HTTP_400_BAD_REQUEST
             )
         mesa = Mesa.objects.filter(id=mesa_id).first()
         if not mesa:
             return Response(
                 {'error':'Mesa no encontrada'},
                 status= status.HTTP_404_NOT_FOUND
             )
         if mesa.estado != 'LIBRE':
             return Response(
                 {'error' : 'La mesa no esta libre'},
                 status= status.HTTP_400_BAD_REQUEST
             )
         comanda = Comanda.objects.create(
             mesa = mesa,
             mozo = request.user
         )
         mesa.estado = 'OCUPADA'
         mesa.save()

         serializer = self.get_serializer(comanda)
         return Response(serializer.data , status=status.HTTP_201_CREATED)


from rest_framework import viewsets, generics, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from mesas.models import Mesa
from .serializers import MesaSerializer

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

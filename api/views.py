
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.db import transaction

from mesas.models import Mesa , UnionMesa
from pedidos.models import Comanda, LineaComanda
from menu.models import Plato
from inventario.models import RecetaInsumo
from caja.models import Pago

from .serializers import MesaSerializer , UnionMesaSerializer,ComandaSerializer,AgregarPlatosRequestSerializer,PagarRequestSerializer



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
    queryset = Comanda.objects.prefetch_related('lineas__plato')
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
                status= status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            mesa = Mesa.objects.select_for_update().filter(id=mesa_id).first()
            if not mesa:
                return Response(
                    {'error':'Mesa no encontrada'},
                    status= status.HTTP_404_NOT_FOUND)
        
            if mesa.estado != 'LIBRE':
                return Response(
                    {'error' : 'La mesa no esta libre'},
                    status= status.HTTP_400_BAD_REQUEST)
        
            comanda = Comanda.objects.create(
                mesa = mesa,
                mozo = request.user)
        
            mesa.estado = 'OCUPADA'
            mesa.save()
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

        if comanda.estado not in ('ABIERTA','LISTA'):
            return Response(
                {'error': 'La comanda no esta abierta'},
                status= status.HTTP_400_BAD_REQUEST
            )

        serializer = AgregarPlatosRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        platos_data = serializer.validated_data['platos']
        errores = []
        platos_a_crear= []

        with transaction.atomic():
            for item in platos_data:
                plato = Plato.objects.filter(id=item['plato_id']).first()
                if not plato:
                    errores.append({'plato_id': item['plato_id'], 'error':'Plato no encontrado'})   
                    continue
                if not plato.disponible:
                    errores.append({'plato_id': item['plato_id'], 'error': 'Plato no dispoible'})
                    continue

                #Verificacion de stock para receta de insumos

                recetas = RecetaInsumo.objects.filter(plato=plato)
                faltantes=[]
                for receta in recetas:
                    necesario= receta.cantidad_por_porcion * item['cantidad']
                    if receta.insumo.stock_actual < necesario:
                        faltantes.append(
                            f"{receta.insumo.nombre}: disponible {receta.insumo.stock_actual}, necesario {necesario}"
                        )
                if faltantes:
                    errores.append({
                        'plato_id': item['plato_id'],
                        'plato': plato.nombre,
                        'error': 'stock insuficiente',
                        'detalle' : faltantes
                    })
                    continue
                platos_a_crear.append(LineaComanda(
                    comanda=comanda,
                    plato=plato,
                    cantidad = item['cantidad'],
                    observacion =item.get('observacion',''),
                ))
            if errores:
                transaction.set_rollback(True)
                return Response({'errores': errores}, status=status.HTTP_400_BAD_REQUEST)
            LineaComanda.objects.bulk_create(platos_a_crear)    
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

            if comanda.estado not in ('ABIERTA','LISTA'):
                return Response(
                    {'error':'La comanda ya fue cobrada o anulada'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            for linea in comanda.lineas.all():
                recetas = RecetaInsumo.objects.filter(plato = linea.plato)
                for receta in recetas:
                    insumo = receta.insumo
                    cantidad_a_descontar= receta.cantidad_por_porcion * linea.cantidad
                    insumo.stock_actual -= cantidad_a_descontar
                    insumo.save()
            Pago.objects.create(
                comanda = comanda,
                metodo = data['metodo'],
                monto = data ['monto'],
                vuelto = data.get('vuelto', 0),
                referencia =data.get('referencia','')
            )

            comanda.estado= 'COBRADA'
            comanda.fecha_cierre = timezone.now()
            comanda.save()

            mesa = comanda.mesa
            mesa.estado = 'LIBRE'
            mesa.save()

        serializer = self.get_serializer(comanda)
        return Response(serializer.data, status=status.HTTP_200_OK)



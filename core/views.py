
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required

#Raiza modificó dashboard_view y añadio los imports de mesa, comanda e insumo
from mesas.models import Mesa
from pedidos.models import Comanda
from inventario.models import Insumo
from django.db import models


def login_view(request):
    if request.method == 'POST':
        # Obtener credenciales del formulario
        username = request.POST.get('username')
        password = request.POST.get('password')

        # Autenticar usuario (Sesion 04 - auth.authenticate)
        user = authenticate(request, username=username, password=password)

        if user is not None:
            # Iniciar sesion si las credenciales son correctas
            login(request, user)
            return redirect('dashboard')
        else:
            # Error: credenciales invalidas
            return render(request, 'auth/login.html', {
                'error': 'Usuario o contrasena incorrectos'
            })

    # GET: mostrar formulario de login
    return render(request, 'auth/login.html')


#segunda modificación by raiza :
@login_required
def dashboard_view(request):
    mesas_libres = Mesa.objects.filter(estado='LIBRE').count()
    mesas_ocupadas = Mesa.objects.filter(estado='OCUPADA').count()
    comandas_activas = Comanda.objects.filter(estado__in=['ABIERTA', 'EN_PREPARACION']).count()
    alertas_stock = Insumo.objects.filter(stock_actual__lt=models.F('stock_minimo')).count()

    context = {
        'mesas_libres': mesas_libres,
        'mesas_ocupadas': mesas_ocupadas,
        'comandas_activas': comandas_activas,
        'alertas_stock': alertas_stock,
    }
    return render(request, 'core/dashboard.html', context)


def logout_view(request):
    logout(request)
    return redirect('login')

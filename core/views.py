
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required


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


@login_required
def dashboard_view(request):
    return render(request, 'core/dashboard.html')


def logout_view(request):
    logout(request)
    return redirect('login')

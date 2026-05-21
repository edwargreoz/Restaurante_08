
#Catálogo de Platos
#Archivo: menu/views.py
#parte del commit: feat: agrego navbar con permisos por rol, mensajes flash y catalogo de platos
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from menu.models import Categoria

@login_required
def catalogo_platos(request):
    categorias = Categoria.objects.prefetch_related('platos').all()
    return render(request, 'menu/catalogo_platos.html', 
                {'categorias': categorias})
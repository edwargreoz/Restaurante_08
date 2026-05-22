
#Catálogo de Platos
#Archivo: menu/views.py
#parte del commit: feat: agrego navbar con permisos por rol, mensajes flash y catalogo de platos
from django.shortcuts import render , redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from core.rol_utils import es_admin
from menu.models import Categoria,Plato

@login_required
def catalogo_platos(request):
    categorias = Categoria.objects.prefetch_related('platos').all()
    return render(request, 'menu/catalogo_platos.html', 
                {'categorias': categorias})

@login_required
@user_passes_test(es_admin)
def gestion_menu(request):
    categorias = Categoria.objects.prefetch_related('platos').all()
    return render(request, 'menu/gestion_menu.html',{'categorias':
                                                     categorias})
@login_required
@user_passes_test(es_admin)
def crear_categoria(request):
    if request.method=='POST':
        nombre = request.POST.get('nombre')
        if nombre:
            Categoria.objects.create(nombre = nombre)
            messages.success(request, 'categoria creada')
        else:
            messages.error(request, 'El nombre es obligatorio')
    return redirect('gestion_menu')

@login_required
@user_passes_test(es_admin)
def crear_plato(request):
    if request.method == 'POST':
        categoria = get_object_or_404(Categoria, id=request.POST.get('categoria'))
        Plato.objects.create(
            categoria = categoria,
            nombre=request.POST.get('nombre'),
            precio=request.POST.get('precio'),
            descripcion = request.POST.get('descripcion',''),
            disponible = request.POST.get('disponible') == 'on',
            imagen=request.FILES.get('imagen'),
        )
        messages.success(request, 'Plato creado')
    return redirect('gestion_menu')

@login_required
@user_passes_test(es_admin)
def editar_plato(request, plato_id):
    plato = get_object_or_404(Plato,id=plato_id)
    if request.method == 'POST':
        plato.nombre = request.POST.get('nombre', plato.nombre)
        plato.precio = request.POST.get('precio', plato.precio)
        plato.descripcion = request.POST.get('descripcion', '')
        plato.disponible = request.POST.get('disponible') == 'on'
        plato.categoria = get_object_or_404(Categoria, id=request.POST.get('categoria'))
        if request.FILES.get('imagen'):
            plato.imagen = request.FILES['imagen']
        plato.save()
        messages.success(request, 'Plato actualizado')
        return redirect ('gestion_menu')
    categorias = Categoria.objects.all()
    return render(request, 'menu/gestion_menu.html', {'editar':plato, 'categorias': categorias
                                                      })
@login_required
@user_passes_test(es_admin)
def eliminar_plato(request, plato_id):
    if request.method == 'POST':
        plato = get_object_or_404(Plato, id=plato_id)
        plato.delete()
        messages.success(request, 'Plato eliminado')
    return redirect('gestion_menu')




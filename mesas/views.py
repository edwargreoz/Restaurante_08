

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.exceptions import ValidationError
from core.rol_utils import es_mozo, es_admin
from .models import Mesa,UnionMesa
from .forms import MesaForm
from pedidos.models import Comanda
from pedidos.views import _procesar_agregar_plato
from menu.models import Categoria


@login_required
@user_passes_test(es_mozo)
def plano_mesas(request): 
    mesas = Mesa.objects.filter(activa=True)
    uniones = UnionMesa.objects.filter(activa=True).prefetch_related('mesas')
    union_mesas_ids = set()
    union_labels = {}
    for union in uniones:
        miembros = list(union.mesas.all())
        nums = sorted([m.numero for m in miembros])
        label = ' + '.join([f'Mesa {x}' for x in nums])
        for m in miembros:
            union_mesas_ids.add(m.id)
            union_labels[m.id] = label
    return render(request, 'mesas/plano_mesas.html', {
        'mesas': mesas,
        'union_mesas_ids': union_mesas_ids,
        'union_labels': union_labels,
    })

@login_required
@user_passes_test(es_mozo)
def detalle_mesa(request, mesa_id):
    mesa = get_object_or_404(Mesa, id=mesa_id)
    comanda_activa = Comanda.objects.filter(
        mesa=mesa, estado__in=['ABIERTA', 'EN_PREPARACION', 'LISTA']
    ).prefetch_related('lineas__plato').first()
    if comanda_activa and mesa.estado == 'LIBRE':
        try:
            comanda_activa.anular(usuario=request.user)
            messages.info(request, 'Se anuló una comanda huérfana de la mesa')
        except ValidationError:
            messages.error(request, 'No se pudo anular la comanda huérfana')
        comanda_activa = None
    union_activa = UnionMesa.objects.filter(mesas=mesa, activa=True).prefetch_related('mesas').first()
    if not comanda_activa and union_activa:
        comanda_activa = Comanda.objects.filter(
            mesa__in=union_activa.mesas.all(),
            estado__in=['ABIERTA', 'EN_PREPARACION', 'LISTA']
        ).prefetch_related('lineas__plato').first()
    categorias = Categoria.objects.prefetch_related('platos').all()
    return render(request, 'mesas/detalle_mesa.html', {
        'mesa': mesa,
        'comanda_activa': comanda_activa,
        'categorias': categorias,
        'union_activa': union_activa,
    })

@login_required
@user_passes_test(es_mozo)
def abrir_comanda(request, mesa_id):
    if request.method == 'POST':
        try:
            Comanda.abrir(mesa_id, request.user)
            messages.success(request, 'Comanda abierta')
        except ValidationError as e:
            messages.error(request, str(e))
    return redirect('detalle_mesa', mesa_id=mesa_id)

@login_required
@user_passes_test(es_mozo)
def agregar_plato_comanda(request, comanda_id):
    comanda = get_object_or_404(Comanda, id=comanda_id)
    if request.method == 'POST':
        _procesar_agregar_plato(request, comanda)
    return redirect('detalle_mesa', mesa_id=comanda.mesa.id)

@login_required
@user_passes_test(es_mozo)
def anular_comanda(request, comanda_id):
    comanda = get_object_or_404(Comanda, id=comanda_id)
    if request.method == 'POST':
        try:
            comanda.anular(usuario=request.user)
            messages.success(request, 'Comanda anulada, mesa liberada')
        except ValidationError as e:
            messages.error(request, str(e))
    return redirect('detalle_mesa', mesa_id=comanda.mesa.id)

@login_required
@user_passes_test(es_mozo)
def marcar_mesa_libre(request, mesa_id):
    mesa = get_object_or_404(Mesa, id=mesa_id)
    if request.method == 'POST' and mesa.estado == 'LIMPIEZA':
        tiene_reserva = mesa.reservas.filter(activa=True).exists()
        union = UnionMesa.objects.filter(mesas=mesa, activa=True).first()
        if union:
            tiene_reserva = tiene_reserva or union.reservas.filter(activa=True).exists()
        
        mesa.estado = 'RESERVADA' if tiene_reserva else 'LIBRE'
        mesa.save(update_fields=['estado'])
        messages.success(request, f'Mesa {mesa.numero} limpiada y ahora está {mesa.get_estado_display().lower()}.')
    return redirect('plano_mesas')

@login_required
@user_passes_test(es_mozo)
def unir_mesas(request):
    mesas = Mesa.objects.filter(activa=True)
    uniones = UnionMesa.objects.filter(activa=True).prefetch_related('mesas')
    if request.method == 'POST':
        mesa_ids = request.POST.getlist('mesas')
        if len(mesa_ids) >= 2:
            mesas_validas = Mesa.objects.filter(id__in=mesa_ids)
            if mesas_validas.count() < 2:
                messages.error(request, 'Las mesas seleccionadas no existen')
                return redirect('unir_mesas')
                
            if mesas_validas.filter(estado='RESERVADA').exists():
                messages.error(request, 'No puedes unir mesas que están reservadas.')
                return redirect('unir_mesas')
            
            # Validar que todas las mesas sean de la misma zona
            zonas = set(m.zona for m in mesas_validas)
            if len(zonas) > 1:
                messages.error(request, 'No puedes unir mesas de diferentes zonas (ej. Salón y Terraza)')
                return redirect('unir_mesas')
            
            selected_ids = set(int(id) for id in mesa_ids)
            for union_existente in uniones:
                union_ids = set(m.id for m in union_existente.mesas.all())
                if union_ids == selected_ids:
                    messages.error(request, 'Ya existe una unión activa con esas mesas')
                    return redirect('unir_mesas')
            
            union = UnionMesa.objects.create()
            union.mesas.set(mesas_validas)
            union.save()
            comandas_activas = Comanda.objects.filter(
                mesa_id__in=mesa_ids,
                estado__in=['ABIERTA', 'EN_PREPARACION', 'LISTA']
            )
            
            if comandas_activas.exists():
                for m in mesas_validas:
                    if m.estado == 'LIBRE':
                        m.estado = 'OCUPADA'
                        m.save()
                        
            if comandas_activas.count() >= 2:
                principal = comandas_activas.first()
                for otras in comandas_activas[1:]:
                    principal.fusionar(otras)
            messages.success(request, 'Unión creada')
            primera = mesas_validas.first()
            return redirect('detalle_mesa', mesa_id=primera.id)
        else:
            messages.error(request, 'Selecciona al menos 2 mesas')
        return redirect('unir_mesas')
    union_mesas_ids = set()
    for u in uniones:
        for m in u.mesas.all():
            union_mesas_ids.add(m.id)
    mesas_disponibles = mesas.exclude(id__in=union_mesas_ids).exclude(estado='RESERVADA')
    return render(request, 'mesas/unir_mesas.html', {
        'mesas': mesas,
        'uniones': uniones,
        'union_mesas_ids': union_mesas_ids,
        'mesas_disponibles': mesas_disponibles,
    })
@login_required
@user_passes_test(es_mozo)
def agregar_mesa_union(request, union_id):
    if request.method == 'POST':
        union = get_object_or_404(UnionMesa, id=union_id, activa=True)
        mesa_id = request.POST.get('mesa_id')
        if mesa_id:
            mesa = get_object_or_404(Mesa, id=mesa_id)
            if union.mesas.filter(id=mesa_id).exists():
                messages.error(request, f'Mesa {mesa.numero} ya está en la unión')
            elif union.esta_reservada():
                messages.error(request, 'La unión está reservada. Modifica la reserva para agregar mesas.')
                return redirect('unir_mesas')
            elif mesa.estado == 'RESERVADA':
                messages.error(request, 'No puedes agregar una mesa que está reservada.')
                return redirect('unir_mesas')
            else:
                # Validar que la mesa sea de la misma zona que las mesas de la unión
                zona_union = union.mesas.first().zona
                if mesa.zona != zona_union:
                    zona_display = dict(Mesa.ZONAS).get(zona_union, zona_union)
                    messages.error(request, f'No puedes agregar una mesa de {mesa.get_zona_display()} a una unión de {zona_display}')
                    return redirect('unir_mesas')
                union.mesas.add(mesa)
                comanda_union = Comanda.objects.filter(
                    mesa__in=union.mesas.all(),
                    estado__in=['ABIERTA', 'EN_PREPARACION', 'LISTA']
                ).exclude(mesa=mesa).first()
                if comanda_union:
                    from caja.models import Caja
                    if not Caja.objects.filter(estado='ABIERTA').exists():
                        messages.error(request, 'No hay un turno de caja abierto')
                        return redirect('unir_mesas')
                    mesa.estado = 'OCUPADA'
                    mesa.save()
                    comanda_nueva = Comanda.objects.create(mesa=mesa, mozo=request.user)
                    comanda_union.fusionar(comanda_nueva)
                else:
                    # Solo intentar abrir comanda si la mesa está libre
                    # Si las mesas están reservadas u ocupadas, solo se agrega a la unión
                    try:
                        Comanda.abrir(mesa.id, request.user)
                    except ValidationError:
                        pass  # La mesa se agrega a la unión sin abrir comanda
                messages.success(request, f'Mesa {mesa.numero} agregada a la unión')
        return redirect('unir_mesas')
    return redirect('unir_mesas')

@login_required
@user_passes_test(es_mozo)
def deshacer_union(request, union_id):
    if request.method == 'POST':
        union = get_object_or_404(UnionMesa, id=union_id, activa=True)
        if union.esta_reservada():
            messages.error(request, 'No puedes deshacer una unión que tiene una reserva activa.')
            return redirect('unir_mesas')
        mesa_ids = [m.id for m in union.mesas.all()]
        comandas_activas = Comanda.objects.filter(
            mesa_id__in=mesa_ids,
            estado__in=['ABIERTA', 'EN_PREPARACION', 'LISTA']
        )
        errores = []
        for comanda in comandas_activas:
            try:
                comanda.anular(usuario=request.user)
            except ValidationError as e:
                errores.append(str(e))
        union.activa = False
        union.save()
        if errores:
            messages.warning(request, 'Unión deshecha, pero algunas comandas no pudieron anularse: ' + '; '.join(errores))
        else:
            messages.success(request, 'Unión deshecha, comandas anuladas, mesas liberadas')
    return redirect('unir_mesas')

# ----------------- VISTAS DE ADMINISTRADOR (CRUD MESAS) -----------------

@login_required
@user_passes_test(es_admin)
def lista_mesas_admin(request):
    if request.method == 'POST':
        form = MesaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Mesa creada exitosamente.')
            return redirect('lista_mesas_admin')
    else:
        form = MesaForm()
        
    mesas = Mesa.objects.filter(activa=True).order_by('numero')
    return render(request, 'mesas/lista_mesas_admin.html', {'mesas': mesas, 'form': form})

@login_required
@user_passes_test(es_admin)
def crear_mesa(request):
    if request.method == 'POST':
        form = MesaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Mesa creada exitosamente.')
            return redirect('lista_mesas_admin')
    else:
        form = MesaForm()
    
    return render(request, 'mesas/form_mesa.html', {'form': form, 'titulo': 'Crear Nueva Mesa'})

@login_required
@user_passes_test(es_admin)
def editar_mesa(request, mesa_id):
    mesa = get_object_or_404(Mesa, id=mesa_id, activa=True)
    if mesa.estado == 'RESERVADA':
        messages.error(request, 'No puedes editar una mesa que actualmente se encuentra RESERVADA.')
        return redirect('lista_mesas_admin')
        
    if request.method == 'POST':
        form = MesaForm(request.POST, instance=mesa)
        if form.is_valid():
            form.save()
            messages.success(request, f'Mesa {mesa.numero} actualizada exitosamente.')
            return redirect('lista_mesas_admin')
    else:
        form = MesaForm(instance=mesa)
    
    return render(request, 'mesas/form_mesa.html', {'form': form, 'titulo': f'Editar Mesa {mesa.numero}'})

@login_required
@user_passes_test(es_admin)
def eliminar_mesa(request, mesa_id):
    mesa = get_object_or_404(Mesa, id=mesa_id, activa=True)
    if request.method == 'POST':
        # Validar si no está en uso actualmente
        if mesa.estado != 'LIBRE':
            messages.error(request, 'No puedes eliminar una mesa que no está LIBRE.')
            return redirect('lista_mesas_admin')
        
        # Borrado lógico
        mesa.activa = False
        mesa.save()
        messages.success(request, f'Mesa {mesa.numero} eliminada lógicamente.')
        return redirect('lista_mesas_admin')
    
    return render(request, 'mesas/eliminar_mesa_confirmar.html', {'mesa': mesa})

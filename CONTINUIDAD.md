
# GUÍA DE CONTINUIDAD — Restaurante_08

---

## 📦 Rama activa: `developer`

Todo el código de mesas + reservas está mergeado. Las demás ramas deben partir de `developer`.

---

## 🧱 Estado actual del proyecto

### ✅ Completado (Módulo Mesas + Reservas)

| Componente | Archivos clave |
|---|---|
| **Modelos** | `mesas/models.py`, `reservas/models.py` — heredan de `ModeloBase` (soft delete) |
| **Service Layer** | `mesas/services.py` (`MesaService`, `UnionMesaService`), `reservas/services.py` (`ReservaService`) |
| **Views (thin)** | `mesas/views.py`, `reservas/views.py` — sin lógica de negocio |
| **API REST** | `api/views.py`, `api/serializers.py` — endpoints para uniones de mesas |
| **WebSocket clients (JS)** | `static/js/mesas/plano_websocket.js`, `static/js/cocina/kds_websocket.js` |
| **Drag & Drop** | `static/js/mesas/drag_drop_unir.js` — unir mesas arrastrando |
| **CSS** | `static/css/mesas/mesas.css` — animaciones, detalle, union cards |
| **Templates** | `templates/mesas/plano_mesas.html`, `detalle_mesa.html` |
| **Hexagonal (bonus)** | `dominio/entidades/` (Mesa, Reserva, UnionMesa), `infraestructura/persistencia/repositorios/` |
| **Excepciones** | `core/excepciones.py` — todas las excepciones del dominio |

### ❌ Pendiente (dependencias externas)

| Tarea | Responsable | Depende de |
|---|---|---|
| Consumers WebSocket (`plano_consumer`, `kds_consumer`) | **edwargreoz** | `config/routing.py` ya existe |
| `pedidos/services.py` con `ComandaService` | **linnexnami** | Modelo `Comanda` ya tiene métodos `abrir()`, `anular()`, `fusionar()` |

---

## 🔧 Reglas obligatorias para todos

### 1. Arquitectura (Service Layer)

```
Vista (views.py) → Service (services.py) → Modelo (models.py)
                      ↕
               core/excepciones.py
```

- Las views **NUNCA** tienen lógica de negocio. Solo llaman al service y capturan excepciones.
- Los services siempre usan `@transaction.atomic` y `select_for_update()` en stock/pagos.

### 2. Excepciones

Usar SIEMPRE las de `core/excepciones.py`:

```python
from core.excepciones import (
    RecursoNoEncontrado, ReglaNegocioViolada, CapacidadExcedida,
    UnionInvalida, CajaNoAbierta, MesaConComandaActiva,
)
```

NUNCA usar `django.core.exceptions.ValidationError` directo.

### 3. Soft Delete

Todos los modelos heredan de `utils.models.ModeloBase` que provee:
- Campo `activo` (booleano)
- Manager `Modelo.activos` (filtra `activo=True`)
- Método `eliminar(usuario)` para borrado lógico

```python
# ✅ Correcto
mesa = Mesa.activos.get(id=1)
mesa.eliminar(usuario=request.user)

# ❌ Incorrecto
mesa = Mesa.objects.get(id=1)
mesa.delete()
```

### 4. Consultas a la BD

```python
# ✅ Correcto
Mesa.activos.filter(estado='LIBRE')
UnionMesa.activos.prefetch_related('mesas')

# ❌ Incorrecto
Mesa.objects.filter(activo=True)
```

Siempre usar `select_related()` / `prefetch_related()` para evitar consultas N+1.

### 5. Domain Entities (Hexagonal)

- `dominio/entidades/` contiene dataclasses puras de Python.
- **NUNCA** importar Django ORM ni modelos acá.
- Las excepciones se importan de `core.excepciones`, no se definen en dominio.

```python
# ✅ Correcto
from core.excepciones import ReglaNegocioViolada

# ❌ Incorrecto
class ReglaNegocioViolada(Exception):
    pass
```

### 6. Frontend (JS)

- Solo JavaScript Vanilla (sin frameworks).
- Usar Fetch API y WebSocket API nativa.
- Incluir CSRF token en todo POST vía JS:

```javascript
function getCSRFToken() {
    var input = document.querySelector('[name=csrfmiddlewaretoken]');
    if (input) return input.value;
    var match = document.cookie.match(/csrftoken=([^;]+)/);
    return match ? match[1] : '';
}
```

---

## 🔌 WebSocket — Lo que necesita edwargreoz

Los JS clients ya conectan a estas URLs:

| Cliente | URL WebSocket | Grupo |
|---|---|---|
| `static/js/mesas/plano_websocket.js` | `/ws/plano/` | `plano` |
| `static/js/cocina/kds_websocket.js` | `/ws/kds/` | `kds` |

El archivo `config/routing.py` ya tiene las rutas definidas:

```python
from django.urls import re_path
from channels.routing import ProtocolTypeRouter, URLRouter

websocket_urlpatterns = [
    re_path(r'ws/plano/$', PlanoConsumer.as_asgi()),
    re_path(r'ws/kds/$', KDSConsumer.as_asgi()),
]
```

**Falta:** Crear `PlanoConsumer` y `KDSConsumer` en `consumers.py` (o `core/consumers.py`).

Los services ya envían notificaciones a estos grupos:

```python
def _notificar_plano():
    channel_layer = get_channel_layer()
    async_to_safe(channel_layer.group_send)(
        'plano', {'type': 'plano_update', 'data': {'action': 'refresh'}}
    )
```

---

## 📋 Pedidos — Lo que necesita linnexnami

Crear `pedidos/services.py` con `ComandaService`:

```python
# pedidos/services.py — ESQUEMA MÍNIMO
from django.db import transaction
from core.excepciones import RecursoNoEncontrado, ReglaNegocioViolada, CajaNoAbierta
from pedidos.models import Comanda
from caja.models import Caja


class ComandaService:
    @staticmethod
    @transaction.atomic
    def abrir(mesa_id: int, usuario) -> Comanda:
        if not Caja.objects.filter(estado='ABIERTA').exists():
            raise CajaNoAbierta('No hay un turno de caja abierto')
        return Comanda.abrir(mesa_id=mesa_id, usuario=usuario)

    @staticmethod
    @transaction.atomic
    def anular(comanda_id: int, usuario) -> Comanda:
        comanda = Comanda.objects.filter(id=comanda_id).first()
        if not comanda:
            raise RecursoNoEncontrado('Comanda no encontrada')
        comanda.anular(usuario=usuario)
        return comanda

    @staticmethod
    @transaction.atomic
    def fusionar(comanda_principal_id: int, comanda_a_fusionar_id: int) -> Comanda:
        principal = Comanda.objects.filter(id=comanda_principal_id).first()
        secundaria = Comanda.objects.filter(id=comanda_a_fusionar_id).first()
        if not principal or not secundaria:
            raise RecursoNoEncontrado('Comanda no encontrada')
        principal.fusionar(secundaria)
        return principal
```

> **Nota:** Actualmente `mesas/services.py` llama a `Comanda.abrir()`, `comanda.anular()`, `principal.fusionar()` directamente como workaround. Una vez creado `ComandaService`, se puede migrar a usarlo.

---

## 🐳 Comandos para trabajar

```bash
# Iniciar contenedores
docker compose up --build -d

# Detener
docker compose down

# Migraciones
docker compose exec web python manage.py migrate

# Nuevas migraciones
docker compose exec web python manage.py makemigrations <app>

# Logs
docker compose logs -f web
```

---

## 🌿 Flujo de trabajo Git

1. Partir de `developer`:
   ```bash
   git checkout developer
   git pull origin developer
   git checkout -b feature/tu-nombre-lo-que-haces
   ```
2. Commits frecuentes con mensajes claros (`feat:`, `fix:`, `refactor:`).
3. Al terminar, mergear a `developer`:
   ```bash
   git checkout developer
   git pull origin developer
   git merge --no-ff feature/tu-rama
   git push origin developer
   ```
4. **NUNCA** hacer push a `main`.

---

## 🧪 Tests

Ejecutar tests antes de mergear:

```bash
docker compose exec web python manage.py test
```

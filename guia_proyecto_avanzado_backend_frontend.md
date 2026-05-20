# Guía de Proyecto — Restaurant-08

**Backend (API REST):** Edwar
**Frontend (Vistas Django + Templates):** Raiza

> Ambos desarrollan las mismas funcionalidades pero con tecnologías distintas:
> - **Edwar** → DRF ViewSets + Serializers (endpoints JSON)
> - **Raiza** → Django `render()` + ORM directo (templates HTML)

---

## 1. Tech Stack

| Componente | Versión |
|------------|---------|
| Python     | 3.11    |
| Django     | 5.0.6   |
| DRF        | 3.15.2  |
| JWT        | simplejwt 5.5.1 |
| BD         | PostgreSQL 15 |
| Contenedor | Docker Compose |
| Frontend   | Django Templates + Bootstrap |

---

## 2. Apps del proyecto

| App | Backend (API) | Frontend (Vistas) |
|-----|:------------:|:-----------------:|
| `core` | ✅ Completo | ❌ Sin vistas web |
| `mesas` | ✅ Completo | ✅ Vistas listas (plano + detalle) |
| `menu` | ❌ Sin ViewSet propio | ❌ Sin vistas web |
| `pedidos` | ⚠️ API lista (6-9 ok) | ❌ Sin vistas web |
| `inventario` | ⚠️ Falta desc. insumos | ❌ Sin vistas web |
| `caja` | ⚠️ Falta pagar y split | ❌ Sin vistas web |
| `api` | 🟡 Tareas 6-11 ok, falta 14, 15, 13 | — |

---

## 3. Modelos (compartidos — ambos los usan)

| Modelo | App | ¿Listo? |
|--------|-----|:-------:|
| `Mesa` | mesas | ✅ |
| `UnionMesa` | mesas | ✅ |
| `Categoria` | menu | ✅ |
| `Plato` | menu | ✅ |
| `Comanda` | pedidos | ✅ |
| `LineaComanda` | pedidos | ✅ |
| `Insumo` | inventario | ✅ |
| `RecetaInsumo` | inventario | ✅ |
| `Caja` | caja | ✅ |
| `Pago` | caja | ✅ |

---

## 4. ¿Qué está completo?

### ✅ Backend (Edwar)

#### API REST endpoints funcionando

| Endpoint | Método | ViewSet / View |
|----------|--------|---------------|
| `POST /api/v1/auth/token/` | POST | TokenObtainPairView |
| `POST /api/v1/auth/token/refresh/` | POST | TokenRefreshView |
| `GET /api/v1/mesas/` | GET | MesaViewSet |
| `GET /api/v1/mesas/{id}/` | GET | MesaViewSet |
| `GET /api/v1/mesas/estado_actual/` | GET | MesaViewSet |
| `GET/POST /api/v1/uniones-mesas/` | GET/POST | UnionMesaViewSet |
| `GET/PUT/DELETE /api/v1/uniones-mesas/{id}/` | GET/PUT/DELETE | UnionMesaViewSet |
| `GET/POST /api/v1/comandas/` | GET/POST | ComandaViewSet |
| `GET/PUT/DELETE /api/v1/comandas/{id}/` | GET/PUT/DELETE | ComandaViewSet |
| `POST /api/v1/comandas/abrir/` | POST | ComandaViewSet.abrir |
| `POST /api/v1/comandas/{id}/agregar_platos/` | POST | ComandaViewSet.agregar_platos |
| `POST /api/v1/comandas/{id}/pagar/` | POST | ComandaViewSet.pagar |
| `GET /api/v1/reportes/ventas-turno/` | GET | ReportesViewSet.ventas_turno |
| `GET/POST /api/v1/lineas-comanda/` | GET/POST | LineaComandaViewSet |
| `GET/PUT/PATCH/DELETE /api/v1/lineas-comanda/{id}/` | GET/PUT/PATCH/DELETE | LineaComandaViewSet |
| `POST /api/v1/lineas-comanda/{id}/enviar_cocina/` | POST | enviar_cocina |
| `PATCH /api/v1/lineas-comanda/{id}/marcar_listo/` | PATCH | marcar_listo |
| `GET /api/v1/cocina/` | GET | CocinaViewSet |

#### Seguridad y filtros
- ✅ JWT (Access 60min, Refresh 7 días)
- ✅ `select_for_update` + `transaction.atomic`
- ✅ Paginación global (15/page)
- ✅ Filtros globales (django-filters, search, ordering)
- ✅ Filtros personalizados: `ComandaFilter`, `PlatoFilter`, `LineaComandaFilter`
- ✅ Permisos por rol: `EsMozo`, `EsCocinero`, `EsCajero`, `EsAdmin`
- ✅ `select_for_update` en stock al pagar (evita race condition)

### ✅ Frontend (Raiza)

#### Vistas Django funcionando

| Vista | App | Template |
|-------|-----|----------|
| `plano_mesas` | mesas | `mesas/plano_mesas.html` |
| `detalle_mesa` | mesas | `mesas/detalle_mesa.html` |

---

## 5. ¿Qué falta por hacer?

### 🔴 Para Edwar (Backend API)

| # | Tarea | Endpoint | Estado |
|---|-------|----------|:------:|
| 10 | **ReportesViewSet** | `GET /api/v1/reportes/ventas-turno/` | ✅ |
| 12 | **Permisos por rol** | EsMozo, EsCocinero, EsCajero, EsAdmin | ✅ |
| 14 | **UnionMesa + flujo** | Al pagar/abrir, gestionar mesas unidas | ⏳ |
| 15 | **Split payment** | Varios métodos de pago en una comanda | ⏳ |
| 13 | **Tests** | Tests de modelos, endpoints y acciones | ⏳ |

#### Detalle de tareas completadas (Edwar)

**Tarea 10 — ReportesViewSet** ✅
```python
GET /api/v1/reportes/ventas-turno/?caja_id=&fecha_desde=&fecha_hasta=
```
- [x] Totales de ventas agrupados por método de pago
- [x] Totales por turno (caja)
- [x] Filtrar por fecha

**Tarea 12 — Permisos personalizados** ✅
- [x] `EsMozo` — solo ver/crear comandas
- [x] `EsCocinero` — solo ver lineas, cambiar a LISTO
- [x] `EsCajero` — solo ejecutar pagos
- [x] `EsAdmin` — acceso total

**Tarea 14 — UnionMesa + flujo**
- [ ] Al abrir comanda en mesa unida, marcar TODAS como OCUPADA
- [ ] Al pagar, liberar todas las mesas de la unión
- [ ] Mostrar capacidad total en detalle

**Tarea 15 — Split payment**
- [ ] Aceptar lista de pagos: `{"pagos": [{"metodo": "EFECTIVO", "monto": 30}, ...]}`
- [ ] Validar suma = total comanda
- [ ] Crear múltiples objetos Pago en una transacción
- [ ] Mantener descuento de insumos y liberación de mesa

**Tarea 13 — Tests**
- [ ] Tests de modelos
- [ ] Tests de API endpoints
- [ ] Tests de acciones (abrir, agregar_platos, pagar, enviar_cocina, marcar_listo)

---

### 🔴 Para Raiza (Frontend — Vistas Django + Templates)

Cada funcionalidad que Edwar expone como API, Raiza la implementa como vista Django con template HTML.
Todas estas vistas usan el ORM directamente (`Modelo.objects.all()`, `render()`), NO consumen la API REST.

| # | Funcionalidad | App | Archivos a crear/modificar |
|---|--------------|-----|---------------------------|
| 1 | **Login funcional** | core | `core/views.py` + `templates/core/login.html` |
| 2 | **Dashboard** con resumen | core | `core/views.py` + `templates/core/dashboard.html` |
| 3 | **Navbar por rol** | core | `templates/core/base.html` |
| 4 | **Unión de Mesas** (crear/deshacer) | mesas | `mesas/views.py` + `templates/mesas/unir_mesas.html` |
| 5 | **Catálogo de Platos** | menu | `menu/views.py` + `templates/menu/catalogo_platos.html` |
| 6 | **CRUD Gestión Menú** | menu | `menu/views.py` + `templates/menu/gestion_menu.html` |
| 7 | **Tomar Pedido** | pedidos | `pedidos/views.py` + `templates/pedidos/tomar_pedido.html` |
| 8 | **Enviar a cocina** (PENDIENTE→EN_PREP) | pedidos | `pedidos/views.py` + `templates/cocina/kds_panel.html` |
| 9 | **KDS — Cocina** (panel + botón LISTO) | pedidos | `pedidos/views.py` + `templates/cocina/kds_panel.html` |
| 10 | **Lista de Insumos** + alertas stock | inventario | `inventario/views.py` + `templates/inventario/lista_insumos.html` |
| 11 | **CRUD Insumos** | inventario | `inventario/views.py` + `templates/inventario/gestion_insumos.html` |
| 12 | **Cobrar Comanda** (ticket + vuelto) | caja | `caja/views.py` + `templates/caja/cobrar_comanda.html` |
| 13 | **Apertura/Cierre Turno** | caja | `caja/views.py` + `templates/caja/apertura_turno.html` |
| 14 | **Reportes Turno** | caja | `caja/views.py` + `templates/reportes/reportes_turno.html` |

#### Reglas de negocio que debe cumplir en sus vistas
- [ ] Navbar con menú según rol (mozo/cocinero/cajero)
- [ ] Alertas visuales de stock bajo en inventario (rojo si stock < stock_minimo)
- [ ] Cálculo automático de vuelto en caja (JavaScript)
- [ ] Tiempo transcurrido en KDS (JS setInterval)
- [ ] Al pagar: descontar insumos y liberar mesa
- [ ] UnionMesa: al abrir comanda, marcar TODAS como OCUPADA; al pagar, liberar todas

---

## 6. Mapeo: Misma funcionalidad, dos implementaciones

Cada fila representa una funcionalidad que **ambos** deben implementar:

| Funcionalidad | Backend (Edwar) | Frontend (Raiza) |
|--------------|:---------------:|:----------------:|
| Login | ✅ JWT Token | ❌ Falta vista login |
| Dashboard | ❌ No aplica (API) | ❌ Falta template |
| CRUD Mesas | ✅ MesaViewSet | ✅ plano + detalle listos |
| UnionMesa | ✅ UnionMesaViewSet | ❌ Falta crear/deshacer unión |
| CRUD Categorías/Platos | ❌ No hay ViewSet (solo models) | ❌ Falta CRUD gestión menú |
| Catálogo platos | ❌ No aplica (API) | ❌ Falta catálogo template |
| Tomar Pedido (agregar platos) | ✅ ComandaViewSet.agregar_platos | ❌ Falta template |
| Enviar a cocina | ✅ LineaComandaViewSet.enviar_cocina | ❌ Falta en KDS |
| KDS (ver pendientes) | ✅ CocinaViewSet | ❌ Falta panel KDS |
| Marcar LISTO | ✅ LineaComandaViewSet.marcar_listo | ❌ Falta botón en KDS |
| Inventario / alertas stock | ❌ No hay endpoint específico | ❌ Falta lista insumos |
| CRUD Insumos | ❌ No hay ViewSet | ❌ Falta gestión insumos |
| Pagar comanda | ✅ ComandaViewSet.pagar | ❌ Falta cobrar template |
| Apertura/Cierre turno | ❌ No hay endpoint | ❌ Falta template |
| Reportes | ✅ ReportesViewSet | ❌ Falta template |
| Filtros búsqueda | ✅ ComandaFilter, PlatoFilter, LineaComandaFilter | ❌ No aplica (ya filtra en views) |
| Permisos por rol | ✅ EsMozo, EsCocinero, EsCajero, EsAdmin | ❌ Falta navbar por rol |
| Split payment | ⏳ Tarea 15 pendiente | ❌ Falta en cobrar |
| Tests | ⏳ Tarea 13 pendiente | ❌ No aplica |

---

## 7. Resumen de avance

| Área | Completado | Pendiente |
|------|:----------:|:---------:|
| Modelos | 10/10 ✅ | 0 |
| Backend (Edwar) — API | 16 endpoints + permisos + filtros ✅ | Tareas 14, 15, 13 |
| Frontend (Raiza) — Vistas | 2 vistas ✅ (plano + detalle) | 14 funcionalidades |
| **Proyecto total** | **~40%** | **~60%** |

---

## 8. Orden sugerido para continuar

### Para Edwar (Backend)
```
1. ✅ Tarea 10 — ReportesViewSet
2. ✅ Tarea 12 — Permisos por rol
3. ⏳ Tarea 14 — UnionMesa + flujo
4. ⏳ Tarea 15 — Split payment
5. ⏳ Tarea 13 — Tests
```

### Para Raiza (Frontend)
```
1. Login + Dashboard (core)
2. Catálogo de Platos + CRUD Menú (menu)
3. Tomar Pedido + KDS (pedidos)
4. Unión de Mesas (mesas)
5. Lista + CRUD Insumos (inventario)
6. Cobrar + Turno + Reportes (caja)
```

---

## 9. Auditoría de código — Correcciones aplicadas

Durante el desarrollo del backend se realizó una auditoría completa del código. Los issues encontrados y corregidos:

| # | Severidad | Archivo | Problema | Solución |
|---|:---------:|---------|----------|----------|
| 1 | 🔴 Crítico | `api/views.py` | Race condition en stock al pagar — `select_for_update` faltante en Insumo | Bloqueo de filas de insumo antes de descontar |
| 2 | 🟡 Alto | `config/urls.py` | Faltaban includes de `menu`, `pedidos`, `inventario`, `caja` | Agregados los 4 includes |
| 3 | 🟡 Alto | `core/views.py` | `caja_actual.last()` devolvía la caja más antigua | Cambiado a `.first()` |
| 4 | 🟢 Bajo | `api/views.py` | Typos en mensajes de error ("dispoible", "comentario...estad") | Corregidos |
| 5 | 🟢 Bajo | `api/views.py` | `ReportessViewSet` con doble 's' | Renombrado a `ReportesViewSet` |
| 6 | 🟡 Alto | `templates/menu/catalogo_platos.html` | Template usaba `platos` sin view que lo pase | Envuelto en `{% if platos %}` |
| 7 | 🟢 Bajo | `guia_proyecto_*.md` | Versión Django incorrecta (6.0.5 vs 5.0.6) | Corregido |

# Gestión para Restaurantes y Food Service

Sistema web de gestión integral para restaurantes: mesas, pedidos, cocina (KDS),
caja, inventario, menú y reservas.

## Stack

| Capa          | Tecnología                                    |
|---------------|-----------------------------------------------|
| Backend       | Python 3.11 / Django 5.0.6                    |
| API           | Django REST Framework 3.15.2 + JWT            |
| Base de datos | PostgreSQL 15                                 |
| Frontend      | Django Templates + Bootstrap 5.3 CDN          |
| Caché/WS      | Redis 7 + Django Channels 4                   |
| Contenedores  | Docker Compose                                |

## Requisitos

- **Docker** + **Docker Compose** (recomendado), o
- Python 3.11+, PostgreSQL 15, Redis 7

## Inicio rápido (Docker)

```bash
docker compose up --build
```

El servidor inicia en `http://localhost:8000`.

### Migraciones y superusuario

```bash
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
```

## Inicio rápido (local)

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Requiere PostgreSQL y Redis corriendo con las credenciales del `.env`.

## Variables de entorno (`.env`)

```env
SECRET_KEY=tu-clave-secreta-aqui
DEBUG=True
ALLOWED_HOSTS=*

DB_ENGINE=django.db.backends.postgresql
DB_NAME=restaurant_db
DB_USER=restaurant_user
DB_PASSWORD=restaurant_pass
DB_HOST=db
DB_PORT=5432

REDIS_HOST=redis
REDIS_PORT=6379
```

## WebSockets

| Endpoint                     | Descripción                              |
|------------------------------|------------------------------------------|
| `ws://localhost:8000/ws/kds/` | Actualizaciones en tiempo real del KDS   |
| `ws://localhost:8000/ws/plano/` | Estado de mesas en tiempo real          |
| `ws://localhost:8000/ws/comanda/<id>/` | Actualizaciones de una comanda específica |

## Documentación API

- Swagger UI: `http://localhost:8000/api/docs/`
- Schema OpenAPI: `http://localhost:8000/api/schema/`

## Tests

```bash
# Con Docker
docker compose exec web python -m pytest --cov=. --cov-report=term

# Sin Docker
python -m pytest tests/ --cov=. --cov-report=term
```

## Módulos

| Módulo         | Descripción                                       |
|----------------|---------------------------------------------------|
| **utils**      | ModeloBase con soft delete y ManagerActivos       |
| **mesas**      | CRUD de mesas, unión de mesas, plano del salón    |
| **pedidos**    | Comandas, líneas de comanda, cocina (KDS)         |
| **menu**       | Categorías, platos, recetas                       |
| **inventario** | Insumos, movimientos, unidad de conversión jerárquica |
| **caja**       | Apertura/cierre de turno, pagos, reportes         |
| **reservas**   | Reservas con unión de mesas                       |
| **core**       | Dashboard, usuarios, autenticación                |
| **api**        | REST endpoints con DRF ViewSets                   |
| **consumers**  | WebSocket consumers (KDS, plano, comanda)         |

## Arquitectura

```
                    ┌─────────────┐
                    │   Cliente   │
                    │  (Browser)  │
                    └──────┬──────┘
                           │ HTTP / WebSocket
                    ┌──────▼──────┐
                    │   Daphne    │
                    │  (ASGI)     │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
       ┌──────▼─────┐ ┌───▼────┐ ┌────▼────┐
       │   Django   │ │Channels│ │  Redis  │
       │   REST API │ │  WS    │ │ (caché) │
       └──────┬─────┘ └───┬────┘ └─────────┘
              │            │
       ┌──────▼────────────▼──────┐
       │     PostgreSQL 15        │
       └──────────────────────────┘
```

## Estructura del proyecto

```
├── api/                # ViewSets, serializers, permissions
├── caja/               # Caja, pagos, turnos
├── config/             # Settings, ASGI, routing, URLs
│   ├── asgi.py
│   ├── routing.py      # WebSocket routing
│   ├── settings.py
│   └── urls.py
├── consumers/          # WebSocket consumers
│   ├── kds_consumer.py
│   ├── plano_consumer.py
│   └── comanda_consumer.py
├── core/               # Dashboard, excepciones
│   └── excepciones.py  # Jerarquía de excepciones de dominio
├── dominio/            # Capa hexagonal (entidades puras)
├── infraestructura/    # Adaptadores Django
├── inventario/         # Insumos, recetas, unidad de conversión
├── menu/               # Categorías, platos
├── mesas/              # Mesas, union de mesas
├── pedidos/            # Comandas, líneas de comanda
├── reservas/           # Reservas
├── templates/          # Templates HTML
├── tests/              # Tests del sistema
├── utils/              # ModeloBase con soft delete
│   └── models.py
├── .env.example        # Variables de entorno de ejemplo
├── docker-compose.yml  # Django + PostgreSQL + Redis
├── Dockerfile
├── requirements.txt
└── manage.py
```

## Credenciales predefinidas

- **Superuser:** `RaizaNat` / `Raiza123`

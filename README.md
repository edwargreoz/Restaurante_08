# Gestión para Restaurantes

Sistema de gestión integral para restaurantes: mesas, pedidos, inventario, caja, reservas y reportes.

## Requisitos

- **Docker** + **Docker Compose** (recomendado), o
- Python 3.11+, PostgreSQL 15

## Stack

| Capa        | Tecnología                                    |
|-------------|-----------------------------------------------|
| Backend     | Django 5.0.6, DRF 3.15.2, SimpleJWT          |
| Base de datos | PostgreSQL 15                               |
| Frontend    | Django Templates + Bootstrap 5.3 CDN          |
| API         | REST en `/api/v1/` con JWT auth               |

## Inicio rápido (Docker)

```bash
docker compose up --build
```

El servidor inicia en `http://localhost:8000`.

### Crear superusuario

```bash
docker exec -it django_app python manage.py createsuperuser
```

Credenciales predefinidas: `RaizaNat` / `Raiza123` (superuser).

## Inicio rápido (local)

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Requiere PostgreSQL corriendo con las credenciales del `.env`.

## Variables de entorno (`.env`)

```env
SECRET_KEY=clave-secreta
DEBUG=True
DB_ENGINE=django.db.backends.postgresql
DB_NAME=restaurant_db
DB_USER=restaurant_user
DB_PASSWORD=restaurant_pass
DB_HOST=db
DB_PORT=5432
```

## Tests

```bash
docker exec django_app python manage.py test inventario.tests caja.tests
```

## API

| Endpoint                    | Método | Auth     |
|-----------------------------|--------|----------|
| `/api/v1/auth/token/`       | POST   | —        |
| `/api/v1/auth/token/refresh/` | POST | —        |
| `/api/v1/mesas/`            | GET/POST | Mozo   |
| `/api/v1/comandas/`         | GET/POST | Mozo   |
| `/api/v1/categorias/`       | GET    | Cualquiera |
| `/api/v1/platos/`           | GET    | Cualquiera |
| `/api/v1/insumos/`          | GET    | Admin     |
| `/api/v1/recetas/`          | GET    | Admin     |
| `/api/v1/reportes/ventas_turno/` | GET | Cajero |

## Módulos

- **mesas** — CRUD de mesas, unión de mesas
- **pedidos** — comandas, lineas, cocina (KDS)
- **menu** — categorías, platos, recetas
- **inventario** — insumos, movimientos, unidad de conversión jerárquica
- **caja** — apertura/cierre de turno, pagos, reportes
- **reservas** — reservas con unión de mesas
- **core** — dashboard, usuarios
- **api** — REST endpoints con DRF ViewSets

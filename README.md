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
| Caché/WS      | Redis 7 (WebSockets + Caché)                  |
| Contenedores  | Docker Compose                                |

## Requisitos

- **Docker** + **Docker Compose** (recomendado), o
- Python 3.11+, PostgreSQL 15

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

| Módulo       | Descripción                                       |
|--------------|---------------------------------------------------|
| **mesas**    | CRUD de mesas, unión de mesas, plano del salón    |
| **pedidos**  | Comandas, líneas de comanda, cocina (KDS)         |
| **menu**     | Categorías, platos, recetas                       |
| **inventario** | Insumos, movimientos, unidad de conversión jerárquica |
| **caja**     | Apertura/cierre de turno, pagos, reportes         |
| **reservas** | Reservas con unión de mesas                       |
| **core**     | Dashboard, usuarios, autenticación                |
| **api**      | REST endpoints con DRF ViewSets                   |

## Credenciales predefinidas

- **Superuser:** `RaizaNat` / `Raiza123`

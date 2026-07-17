import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Importar desde routing.py que ya define ProtocolTypeRouter
# con HTTP + WebSockets (KDS, plano, comanda)
from config.routing import application  # noqa: E402
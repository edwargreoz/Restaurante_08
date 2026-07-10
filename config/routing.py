from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.urls import re_path
from django.core.asgi import get_asgi_application
from consumers import kds_consumer, plano_consumer, comanda_consumer

websocket_urlpatterns = [
    re_path(r'ws/kds/$', kds_consumer.KDSConsumer.as_asgi()),
    re_path(r'ws/plano/$', plano_consumer.PlanoConsumer.as_asgi()),
    re_path(r'ws/comanda/(?P<comanda_id>\d+)/$', comanda_consumer.ComandaConsumer.as_asgi()),
]

application = ProtocolTypeRouter({
    'http': get_asgi_application(),
    'websocket': AuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})
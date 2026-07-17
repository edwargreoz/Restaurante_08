import logging

logger = logging.getLogger(__name__)


class ChannelsNotificadorPlano:
    def notificar_refresh(self) -> None:
        try:
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                'plano', {'type': 'plano_update', 'data': {'action': 'refresh'}}
            )
        except Exception:
            logger.debug('No se pudo notificar al plano (channels no disponible)')


class ChannelsNotificadorKDS:
    def notificar_refresh(self) -> None:
        try:
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                'kds', {'type': 'kds_update', 'data': {'action': 'refresh'}}
            )
        except (ConnectionError, OSError, TimeoutError):
            pass


class ChannelsNotificadorComanda:
    def notificar_comanda(self, comanda_id: int) -> None:
        try:
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f'comanda_{comanda_id}',
                {'type': 'comanda_update', 'data': {'action': 'refresh', 'comanda_id': comanda_id}}
            )
        except (ConnectionError, OSError, TimeoutError):
            pass

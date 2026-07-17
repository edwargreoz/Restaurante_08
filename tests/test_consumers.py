import json
import pytest
from unittest.mock import MagicMock
from channels.testing import WebsocketCommunicator
from consumers.kds_consumer import KDSConsumer
from consumers.plano_consumer import PlanoConsumer
from consumers.comanda_consumer import ComandaConsumer


def _make_user(is_anonymous=False):
    user = MagicMock()
    user.is_anonymous = is_anonymous
    user.id = 1
    user.username = 'testuser'
    return user


@pytest.mark.asyncio
async def test_conexion_y_desconexion_kds():
    communicator = WebsocketCommunicator(KDSConsumer.as_asgi(), "/ws/kds/")
    communicator.scope['user'] = _make_user()
    connected, _ = await communicator.connect()
    assert connected
    await communicator.disconnect()


@pytest.mark.asyncio
async def test_enviar_mensaje_kds_no_error():
    communicator = WebsocketCommunicator(KDSConsumer.as_asgi(), "/ws/kds/")
    communicator.scope['user'] = _make_user()
    await communicator.connect()
    await communicator.send_json_to({"type": "kds_update", "data": {"comanda": 1}})
    await communicator.disconnect()


@pytest.mark.asyncio
async def test_conexion_y_desconexion_plano():
    communicator = WebsocketCommunicator(PlanoConsumer.as_asgi(), "/ws/plano/")
    communicator.scope['user'] = _make_user()
    connected, _ = await communicator.connect()
    assert connected
    await communicator.disconnect()


@pytest.mark.asyncio
async def test_enviar_mensaje_plano_no_error():
    communicator = WebsocketCommunicator(PlanoConsumer.as_asgi(), "/ws/plano/")
    communicator.scope['user'] = _make_user()
    await communicator.connect()
    await communicator.send_json_to({"type": "plano_update", "data": {"mesa": 5}})
    await communicator.disconnect()


@pytest.mark.asyncio
async def test_conexion_comanda_individual():
    communicator = WebsocketCommunicator(
        ComandaConsumer.as_asgi(), "/ws/comanda/1/"
    )
    communicator.scope['user'] = _make_user()
    communicator.scope['url_route'] = {'kwargs': {'comanda_id': '1'}}
    connected, _ = await communicator.connect()
    assert connected
    await communicator.disconnect()


@pytest.mark.asyncio
async def test_enviar_mensaje_comanda_no_error():
    communicator = WebsocketCommunicator(
        ComandaConsumer.as_asgi(), "/ws/comanda/1/"
    )
    communicator.scope['user'] = _make_user()
    communicator.scope['url_route'] = {'kwargs': {'comanda_id': '1'}}
    await communicator.connect()
    await communicator.send_json_to({"type": "comanda_update", "data": {"estado": "LISTA"}})
    await communicator.disconnect()


@pytest.mark.asyncio
async def test_anonimo_rechazado_kds():
    communicator = WebsocketCommunicator(KDSConsumer.as_asgi(), "/ws/kds/")
    communicator.scope['user'] = _make_user(is_anonymous=True)
    connected, _ = await communicator.connect()
    assert not connected


@pytest.mark.asyncio
async def test_anonimo_rechazado_plano():
    communicator = WebsocketCommunicator(PlanoConsumer.as_asgi(), "/ws/plano/")
    communicator.scope['user'] = _make_user(is_anonymous=True)
    connected, _ = await communicator.connect()
    assert not connected


@pytest.mark.asyncio
async def test_anonimo_rechazado_comanda():
    communicator = WebsocketCommunicator(
        ComandaConsumer.as_asgi(), "/ws/comanda/1/"
    )
    communicator.scope['user'] = _make_user(is_anonymous=True)
    communicator.scope['url_route'] = {'kwargs': {'comanda_id': '1'}}
    connected, _ = await communicator.connect()
    assert not connected

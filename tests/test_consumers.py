import json
import pytest
from channels.testing import WebsocketCommunicator
from consumers.kds_consumer import KDSConsumer
from consumers.plano_consumer import PlanoConsumer
from consumers.comanda_consumer import ComandaConsumer


@pytest.mark.asyncio
async def test_conexion_y_desconexion_kds():
    communicator = WebsocketCommunicator(KDSConsumer.as_asgi(), "/ws/kds/")
    connected, _ = await communicator.connect()
    assert connected
    await communicator.disconnect()


@pytest.mark.asyncio
async def test_enviar_mensaje_kds_no_error():
    communicator = WebsocketCommunicator(KDSConsumer.as_asgi(), "/ws/kds/")
    await communicator.connect()
    await communicator.send_json_to({"type": "kds_update", "data": {"comanda": 1}})
    await communicator.disconnect()


@pytest.mark.asyncio
async def test_conexion_y_desconexion_plano():
    communicator = WebsocketCommunicator(PlanoConsumer.as_asgi(), "/ws/plano/")
    connected, _ = await communicator.connect()
    assert connected
    await communicator.disconnect()


@pytest.mark.asyncio
async def test_enviar_mensaje_plano_no_error():
    communicator = WebsocketCommunicator(PlanoConsumer.as_asgi(), "/ws/plano/")
    await communicator.connect()
    await communicator.send_json_to({"type": "plano_update", "data": {"mesa": 5}})
    await communicator.disconnect()


@pytest.mark.asyncio
async def test_conexion_comanda_individual():
    communicator = WebsocketCommunicator(
        ComandaConsumer.as_asgi(), "/ws/comanda/1/"
    )
    communicator.scope['url_route'] = {'kwargs': {'comanda_id': '1'}}
    connected, _ = await communicator.connect()
    assert connected
    await communicator.disconnect()


@pytest.mark.asyncio
async def test_enviar_mensaje_comanda_no_error():
    communicator = WebsocketCommunicator(
        ComandaConsumer.as_asgi(), "/ws/comanda/1/"
    )
    communicator.scope['url_route'] = {'kwargs': {'comanda_id': '1'}}
    await communicator.connect()
    await communicator.send_json_to({"type": "comanda_update", "data": {"estado": "LISTA"}})
    await communicator.disconnect()

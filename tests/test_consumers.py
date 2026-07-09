import json
from channels.testing import WebsocketCommunicator
from django.test import TransactionTestCase
from config.routing import application


class KDSConsumerTest(TransactionTestCase):
    async def test_conexion_y_desconexion_kds(self):
        communicator = WebsocketCommunicator(application, "ws/kds/")
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        await communicator.disconnect()

    async def test_enviar_mensaje_kds_no_error(self):
        communicator = WebsocketCommunicator(application, "ws/kds/")
        await communicator.connect()
        await communicator.send_json_to({"type": "kds_update", "data": {"comanda": 1}})
        await communicator.disconnect()


class PlanoConsumerTest(TransactionTestCase):
    async def test_conexion_y_desconexion_plano(self):
        communicator = WebsocketCommunicator(application, "ws/plano/")
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        await communicator.disconnect()

    async def test_enviar_mensaje_plano_no_error(self):
        communicator = WebsocketCommunicator(application, "ws/plano/")
        await communicator.connect()
        await communicator.send_json_to({"type": "plano_update", "data": {"mesa": 5}})
        await communicator.disconnect()


class ComandaConsumerTest(TransactionTestCase):
    async def test_conexion_comanda_individual(self):
        communicator = WebsocketCommunicator(application, "ws/comanda/1/")
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        await communicator.disconnect()

    async def test_enviar_mensaje_comanda_no_error(self):
        communicator = WebsocketCommunicator(application, "ws/comanda/1/")
        await communicator.connect()
        await communicator.send_json_to({"type": "comanda_update", "data": {"estado": "LISTA"}})
        await communicator.disconnect()

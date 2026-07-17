import json
from channels.generic.websocket import AsyncWebsocketConsumer


class PlanoConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        if self.scope["user"].is_anonymous:
            await self.close()
            return
        self.group_name = 'plano'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        pass

    async def plano_update(self, event):
        await self.send(text_data=json.dumps(event['data']))
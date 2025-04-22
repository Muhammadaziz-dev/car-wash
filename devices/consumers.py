# devices/consumers.py

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Device


class DeviceStatusConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.device_id = self.scope['url_route']['kwargs']['device_id']
        self.device_group_name = f'device_{self.device_id}'

        # Join device group
        await self.channel_layer.group_add(
            self.device_group_name,
            self.channel_name
        )

        await self.accept()

        # Send initial device status
        device_data = await self.get_device_data(self.device_id)
        if device_data:
            await self.send(text_data=json.dumps(device_data))

    async def disconnect(self, close_code):
        # Leave device group
        await self.channel_layer.group_discard(
            self.device_group_name,
            self.channel_name
        )

    # Receive message from WebSocket
    async def receive(self, text_data):
        # Handle commands from frontend if needed
        pass

    # Receive message from device group
    async def device_update(self, event):
        # Send message to WebSocket
        message = event.get('message', {})
        await self.send(text_data=json.dumps(message))

    @database_sync_to_async
    def get_device_data(self, device_id):
        try:
            device = Device.objects.get(id=device_id)
            return {
                'id': device.id,
                'name': device.name,
                'status': device.status,
                'is_active': device.is_active,
                'last_seen': device.last_seen.isoformat() if device.last_seen else None,
                # Add other fields as needed
            }
        except Device.DoesNotExist:
            return None
# devices/utils.py

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

def broadcast_device_update(device_id, message):
    """
    Broadcast a device update to all connected WebSocket clients
    """
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f'device_{device_id}',
        {
            'type': 'device_update',
            'message': message
        }
    )
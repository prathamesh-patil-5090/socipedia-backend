from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import Notification
from .serializers import NotificationSerializer

def send_notification_websocket(user_id, notification):
    """
    Send a real-time notification via WebSocket
    """
    channel_layer = get_channel_layer()
    group_name = f'notifications_{user_id}'
    
    # Check if it's a notification object or a dict (for invalidation messages)
    if isinstance(notification, dict):
        # It's an invalidation message
        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                'type': 'friend_request_invalid',
                'notification_id': notification.get('notification_id'),
                'message': notification.get('message')
            }
        )
    else:
        # It's a regular notification
        serializer = NotificationSerializer(notification)
        notification_data = serializer.data
        
        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                'type': 'notification_message',
                'notification': notification_data
            }
        )

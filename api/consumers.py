import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from .models import Notification
from .serializers import NotificationSerializer
from urllib.parse import parse_qs

User = get_user_model()


class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user_id = self.scope['url_route']['kwargs']['user_id']
        self.group_name = f'notifications_{self.user_id}'
        
        print(f"WebSocket connecting for user {self.user_id}")
        
        # Get token from query string
        query_string = self.scope.get('query_string', b'').decode()
        query_params = parse_qs(query_string)
        token = query_params.get('token', [None])[0]
        
        if not token:
            print("No token provided in WebSocket connection")
            await self.close()
            return
            
        # Verify JWT token and get user
        try:
            access_token = AccessToken(token)
            user_id_from_token = access_token['user_id']
            user = await self.get_user(user_id_from_token)
            
            if not user:
                print(f"User not found for token user_id: {user_id_from_token}")
                await self.close()
                return
                
            if str(user.id) != str(self.user_id):
                print(f"User ID mismatch: token={user.id}, url={self.user_id}")
                await self.close()
                return
                
            self.user = user
            print(f"WebSocket authenticated successfully for user {self.user.username}")
        except (InvalidToken, TokenError) as e:
            print(f"Token validation error: {e}")
            await self.close()
            return
        except Exception as e:
            print(f"Unexpected error in WebSocket connect: {e}")
            await self.close()
            return
        
        # Join notification group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        
        await self.accept()
        print(f"WebSocket accepted for user {self.user.username}")
        
        # Send existing unread notifications on connect
        await self.send_unread_notifications()

    async def disconnect(self, close_code):
        print(f"WebSocket disconnecting for user {getattr(self, 'user_id', 'unknown')}, close_code: {close_code}")
        # Leave notification group
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'mark_as_read':
                notification_id = data.get('notification_id')
                if notification_id:
                    await self.mark_notification_as_read(notification_id)
                    
        except json.JSONDecodeError:
            pass

    async def notification_message(self, event):
        """Send notification to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'notification': event['notification']
        }))

    async def friend_request_invalid(self, event):
        """Send friend request invalid message to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'friend_request_invalid',
            'notification_id': event['notification_id'],
            'message': event['message']
        }))

    @database_sync_to_async
    def get_user(self, user_id):
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None

    @database_sync_to_async
    def get_unread_notifications(self):
        notifications = Notification.objects.filter(
            user_id=self.user_id,
            is_read=False
        ).order_by('-created_at')[:20]  # Limit to last 20 unread
        
        serializer = NotificationSerializer(notifications, many=True)
        return serializer.data

    @database_sync_to_async
    def mark_notification_as_read(self, notification_id):
        try:
            notification = Notification.objects.get(
                id=notification_id,
                user_id=self.user_id
            )
            notification.is_read = True
            notification.save()
            return True
        except Notification.DoesNotExist:
            return False

    async def send_unread_notifications(self):
        """Send all unread notifications when user connects"""
        notifications = await self.get_unread_notifications()
        
        await self.send(text_data=json.dumps({
            'type': 'unread_notifications',
            'notifications': notifications
        }))

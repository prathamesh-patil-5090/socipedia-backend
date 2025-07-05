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

class MessageConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        self.conversation_group_name = f'conversation_{self.conversation_id}'
        
        print(f"[WebSocket] Connecting to conversation {self.conversation_id}")
        
        # Get token from query string
        query_string = self.scope.get('query_string', b'').decode()
        query_params = parse_qs(query_string)
        token = query_params.get('token', [None])[0]
        
        if not token:
            print("[WebSocket] No token provided - closing connection")
            await self.close(code=1008)  # Policy violation
            return
            
        # Verify JWT token and get user
        try:
            access_token = AccessToken(token)
            user_id_from_token = access_token['user_id']
            user = await self.get_user(user_id_from_token)
            
            if not user:
                print(f"[WebSocket] User not found for token user_id: {user_id_from_token}")
                await self.close(code=1008)  # Policy violation
                return
                
            self.user = user
            print(f"[WebSocket] Authenticated user: {self.user.username} (ID: {self.user.id})")
            
            # Check if user is participant in conversation
            is_participant = await self.check_conversation_participant()
            if not is_participant:
                print(f"[WebSocket] User {self.user.id} is not a participant in conversation {self.conversation_id}")
                await self.close(code=1008)  # Policy violation
                return
                
        except (InvalidToken, TokenError) as e:
            print(f"[WebSocket] Token validation failed: {e}")
            await self.close(code=1008)  # Policy violation
            return
        except Exception as e:
            print(f"[WebSocket] Connection error: {e}")
            await self.close(code=1011)  # Server error
            return

        # Join conversation group
        await self.channel_layer.group_add(
            self.conversation_group_name,
            self.channel_name
        )
        await self.accept()
        print(f"[WebSocket] Connection accepted for conversation {self.conversation_id} (user: {self.user.username})")
        
        # Send connection confirmation
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'conversation_id': self.conversation_id,
            'user_id': self.user.id,
            'message': 'Connected to conversation'
        }))

    async def disconnect(self, close_code):
        username = getattr(self, 'user', None)
        if username:
            username = getattr(username, 'username', 'unknown')
        else:
            username = 'unknown'
        
        print(f"[WebSocket] Disconnecting from conversation {self.conversation_id} (code: {close_code}, user: {username})")
        # Leave conversation group
        if hasattr(self, 'conversation_group_name'):
            await self.channel_layer.group_discard(
                self.conversation_group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        if not hasattr(self, 'user'):
            print("[WebSocket] Received message from unauthenticated connection")
            await self.close(code=1008)
            return
            
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            print(f"[WebSocket] Received message type: {message_type} from user {self.user.username}")
            
            if message_type == 'typing':
                # Handle typing indicator
                await self.channel_layer.group_send(
                    self.conversation_group_name,
                    {
                        'type': 'typing_indicator',
                        'user_id': self.user.id,
                        'username': self.user.username,
                        'is_typing': data.get('is_typing', False)
                    }
                )
            elif message_type == 'message':
                # Handle new message
                message_data = data.get('message', {})
                content = message_data.get('content', '').strip()
                
                if content:
                    # Create message in database
                    message = await self.create_message(content)
                    if message:
                        # Serialize message with full data
                        serialized_message = await self.serialize_message(message)
                        if serialized_message:
                            # Broadcast message to conversation group
                            await self.channel_layer.group_send(
                                self.conversation_group_name,
                                {
                                    'type': 'new_message',
                                    'message': serialized_message
                                }
                            )
                            print(f"[WebSocket] Message broadcasted for conversation {self.conversation_id}")
                        else:
                            print(f"[WebSocket] Failed to serialize message")
                    else:
                        print(f"[WebSocket] Failed to create message")
                else:
                    print(f"[WebSocket] Empty message content received")
            else:
                print(f"[WebSocket] Unknown message type: {message_type}")
                        
        except json.JSONDecodeError as e:
            print(f"[WebSocket] Invalid JSON received: {e}")
        except Exception as e:
            print(f"[WebSocket] Error processing message: {e}")

    async def typing_indicator(self, event):
        # Send typing indicator to WebSocket (don't send to self)
        if event['user_id'] != self.user.id:
            await self.send(text_data=json.dumps({
                'type': 'typing',
                'user_id': event['user_id'],
                'username': event['username'],
                'is_typing': event['is_typing']
            }))

    async def new_message(self, event):
        # Send new message to WebSocket
        message_data = event['message']
        print(f"[WebSocket] Sending new message to user {self.user.username}: {message_data.get('id', 'unknown')}")
        await self.send(text_data=json.dumps({
            'type': 'message',
            'message': message_data
        }))

    async def message_edited(self, event):
        # Send edited message to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'message_edited',
            'message': event['message']
        }))

    async def message_deleted(self, event):
        # Send deleted message notification to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'message_deleted',
            'message_id': event['message_id']
        }))

    @database_sync_to_async
    def get_user(self, user_id):
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None

    @database_sync_to_async
    def check_conversation_participant(self):
        try:
            from .models import Conversation
            conversation = Conversation.objects.get(id=self.conversation_id)
            return conversation.participants.filter(id=self.user.id).exists()
        except:
            return False

    @database_sync_to_async
    def create_message(self, content):
        try:
            from .models import Conversation, Message
            from django.utils import timezone
            
            print(f"[WebSocket] Creating message: user={self.user.id}, conversation={self.conversation_id}, content='{content[:50]}...'")
            
            conversation = Conversation.objects.get(
                id=self.conversation_id,
                participants=self.user
            )
            
            print(f"[WebSocket] Found conversation: {conversation.id}, participants: {[p.id for p in conversation.participants.all()]}")
            
            message = Message.objects.create(
                conversation=conversation,
                sender=self.user,
                content=content
            )
            
            print(f"[WebSocket] Message created successfully: {message.id}")
            
            # Update conversation timestamp
            conversation.updated_at = timezone.now()
            conversation.save()
            
            return message
        except Conversation.DoesNotExist:
            print(f"[WebSocket] Error: Conversation {self.conversation_id} not found or user {self.user.id} is not a participant")
            return None
        except Exception as e:
            print(f"[WebSocket] Error creating message: {e}")
            import traceback
            traceback.print_exc()
            return None

    @database_sync_to_async
    def serialize_message(self, message):
        try:
            from .serializers import MessageSerializer
            from django.http import HttpRequest
            
            # Create a mock request for proper URL building
            request = HttpRequest()
            request.META['HTTP_HOST'] = 'localhost:8000'
            request.META['SERVER_NAME'] = 'localhost'
            request.META['SERVER_PORT'] = '8000'
            
            serializer = MessageSerializer(message, context={'request': request})
            data = serializer.data
            
            print(f"[WebSocket] Serialized message {message.id} - sender: {data.get('sender', {}).get('username', 'unknown')}")
            return data
        except Exception as e:
            print(f"[WebSocket] Error serializing message: {e}")
            return None

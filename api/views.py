from django.shortcuts import render
from django.shortcuts import render
from rest_framework import generics, status, viewsets, serializers
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAuthenticatedOrReadOnly
from django.contrib.auth import get_user_model, authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from .models import Post, Comment, User, FriendRequest, Notification, Conversation, Message, MessageReadStatus
from .serializers import UserSerializer, PostSerializer, CommentSerializer, FriendRequestSerializer, NotificationSerializer, ConversationSerializer, MessageSerializer
from .pagination import PostsPagination
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.http import HttpResponse, Http404
from django.conf import settings
import os
from rest_framework.decorators import api_view, permission_classes
import requests
import json
from django.core.files.base import ContentFile
from urllib.parse import urlencode
import secrets
import string
from django.db.models import Q
from .websocket_utils import send_notification_websocket
from django.utils import timezone

# Helper function to invalidate friend request notifications
def invalidate_friend_request_notifications(friend_request_id):
    """
    Mark friend request notifications as invalid and notify users via WebSocket
    """
    try:
        # Find all notifications related to this friend request
        notifications = Notification.objects.filter(
            friend_request_id=friend_request_id,
            type=Notification.FRIEND_REQUEST,
            is_read=False
        )
        
        for notification in notifications:
            # Send WebSocket message to notify that the friend request is invalid
            send_notification_websocket(notification.user.id, {
                'type': 'friend_request_invalid',
                'notification_id': notification.id,
                'message': 'Friend request is no longer available'
            })
            
            # Mark notification as read (or delete it)
            notification.is_read = True
            notification.save()
            
    except Exception as e:
        print(f"Error invalidating friend request notifications: {e}")


def are_friends(user1, user2):
    """Check if two users are friends"""
    return user1.friends.filter(id=user2.id).exists()

User = get_user_model()

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = UserSerializer
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Generate random profile stats like in Express version
        import random
        user.viewed_profile = random.randint(0, 10000)
        user.impressions = random.randint(0, 10000)
        user.save()
        
        return Response({
            'user': UserSerializer(user).data,
            'message': 'Registration successful'
        }, status=status.HTTP_201_CREATED)

class LoginView(generics.GenericAPIView):
    permission_classes = (AllowAny,)

    def post(self, request, *args, **kwargs):
        username_or_email = request.data.get("username")
        password = request.data.get("password")
        
        # Try to authenticate with username first
        user = authenticate(username=username_or_email, password=password)
        
        # If authentication failed and input looks like email, try email authentication
        if not user and '@' in username_or_email:
            try:
                user_obj = User.objects.get(email=username_or_email)
                user = authenticate(username=user_obj.username, password=password)
            except User.DoesNotExist:
                pass
        
        if user:
            refresh = RefreshToken.for_user(user)
            return Response({
                'user': UserSerializer(user).data,
                'token': str(refresh.access_token),
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            })
        return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

class UserDetailView(generics.RetrieveAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @action(detail=True, methods=['patch'])
    def upload_picture(self, request, pk=None):
        user = self.get_object()
        if 'picture' in request.FILES:
            user.picture = request.FILES['picture']
            user.save()
            serializer = UserSerializer(user)
            return Response(serializer.data)
        return Response({'error': 'No picture provided'}, status=400)

    @action(detail=True, methods=['get'])
    def comments(self, request, pk=None):
        user = self.get_object()
        comments = Comment.objects.filter(user=user)
        serializer = CommentSerializer(comments, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def add_friend(self, request, pk=None):
        if not request.user.is_authenticated:
            return Response({'error': 'Authentication required to add friends'}, status=401)
            
        user = self.get_object()
        friend_id = request.data.get('friend_id')
        friend = User.objects.get(id=friend_id)
        user.friends.add(friend)
        return Response({'status': 'friend added'})

    @action(detail=True, methods=['post'])
    def remove_friend(self, request, pk=None):
        if not request.user.is_authenticated:
            return Response({'error': 'Authentication required to remove friends'}, status=401)
            
        user = self.get_object()
        friend_id = request.data.get('friend_id')
        friend = User.objects.get(id=friend_id)
        user.friends.remove(friend)
        return Response({'status': 'friend removed'})

class PostListView(generics.ListCreateAPIView):
    serializer_class = PostSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    pagination_class = PostsPagination

    def get_queryset(self):
        queryset = Post.objects.all().order_by('-created_at')
        user_id = self.request.query_params.get('user', None)
        if user_id is not None:
            queryset = queryset.filter(user__id=user_id)
        return queryset

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class PostDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Post.objects.all()
    serializer_class = PostSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

class PostViewSet(viewsets.ModelViewSet):
    serializer_class = PostSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    pagination_class = PostsPagination

    def get_queryset(self):
        queryset = Post.objects.all().order_by('-created_at')
        user_id = self.request.query_params.get('user', None)
        if user_id is not None:
            queryset = queryset.filter(user__id=user_id)
        return queryset

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'])
    def like(self, request, pk=None):
        if not request.user.is_authenticated:
            return Response({'error': 'Authentication required to like posts'}, status=401)
            
        post = self.get_object()
        user = request.user
        
        if user in post.likes.all():
            post.likes.remove(user)
            liked = False
        else:
            post.likes.add(user)
            liked = True
            
            # Create notification for post owner (if not liking own post)
            if post.user != user:
                # Check if there's already a recent like notification from this user for this post
                from django.utils import timezone
                from datetime import timedelta
                
                existing_notification = Notification.objects.filter(
                    user=post.user,
                    from_user=user,
                    type=Notification.POST_LIKE,
                    post=post,
                    created_at__gte=timezone.now() - timedelta(hours=1)  # Check for notifications in the last hour
                ).first()
                
                if not existing_notification:
                    notification = Notification.objects.create(
                        user=post.user,
                        type=Notification.POST_LIKE,
                        message=f"{user.first_name} {user.last_name} liked your post",
                        post=post,
                        from_user=user
                    )
                    
                    # Send real-time notification via WebSocket
                    send_notification_websocket(post.user.id, notification)
                else:
                    # Update the existing notification timestamp without creating a new one
                    existing_notification.created_at = timezone.now()
                    existing_notification.is_read = False  # Mark as unread
                    existing_notification.save()
                    
                    # Don't send WebSocket message for updated notifications to avoid duplicates
            
        return Response({
            'liked': liked,
            'likes_count': post.likes.count()
        })

    def perform_update(self, serializer):
        # Ensure user can only update their own posts
        if serializer.instance.user != self.request.user:
            return Response({'error': 'You can only update your own posts'}, status=403)
        serializer.save()

    def destroy(self, request, *args, **kwargs):
        """Custom destroy method to ensure users can only delete their own posts"""
        post = self.get_object()
        
        # Check if user owns the post
        if post.user != request.user:
            return Response({'error': 'You can only delete your own posts'}, status=status.HTTP_403_FORBIDDEN)
        
        # Delete the post
        post.delete()
        
        return Response({'message': 'Post deleted successfully'}, status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['patch'])
    def upload_picture(self, request, pk=None):
        post = self.get_object()
        # Check if user owns the post
        if post.user != request.user:
            return Response({'error': 'You can only update your own posts'}, status=403)
            
        if 'picture' in request.FILES:
            post.picture = request.FILES['picture']
            post.save()
            serializer = PostSerializer(post)
            return Response(serializer.data)
        return Response({'error': 'No picture provided'}, status=400)

    @action(detail=True, methods=['patch'])
    def update_post(self, request, pk=None):
        post = self.get_object()
        # Check if user owns the post
        if post.user != request.user:
            return Response({'error': 'You can only update your own posts'}, status=403)
            
        # Update description and/or picture
        if 'description' in request.data:
            post.description = request.data['description']
        
        if 'picture' in request.FILES:
            post.picture = request.FILES['picture']
        
        post.save()
        serializer = PostSerializer(post)
        return Response(serializer.data)

class CommentListView(generics.ListCreateAPIView):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def perform_create(self, serializer):
        post = Post.objects.get(id=self.kwargs['post_id'])
        serializer.save(user=self.request.user, post=post)

class CommentDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def perform_create(self, serializer):
        post = Post.objects.get(id=self.request.data.get('post_id'))
        comment = serializer.save(user=self.request.user, post=post)
        
        # Create notification for post owner (if not commenting on own post)
        if post.user != self.request.user:
            notification = Notification.objects.create(
                user=post.user,
                type=Notification.POST_COMMENT,
                message=f"{self.request.user.first_name} {self.request.user.last_name} commented on your post",
                post=post,
                from_user=self.request.user
            )
            
            # Send real-time notification via WebSocket
            send_notification_websocket(post.user.id, notification)

    @action(detail=True, methods=['post'])
    def like(self, request, pk=None):
        if not request.user.is_authenticated:
            return Response({'error': 'Authentication required to like comments'}, status=401)
            
        comment = self.get_object()
        user = request.user
        
        if user in comment.likes.all():
            comment.likes.remove(user)
            liked = False
        else:
            comment.likes.add(user)
            liked = True
            
        return Response({
            'liked': liked,
            'likes_count': comment.likes.count()
        })

@api_view(['GET'])
@permission_classes([AllowAny])
def serve_image(request, path):
    file_path = os.path.join(settings.MEDIA_ROOT, path)
    if not os.path.exists(file_path):
        raise Http404("Image not found")

    with open(file_path, 'rb') as f:
        return HttpResponse(f.read(), content_type="image/jpeg")


@api_view(['POST'])
@permission_classes([AllowAny])
def google_oauth_callback(request):
    """
    Handle Google OAuth callback and process JWT token from react-google-login
    """
    try:
        token = request.data.get('token')
        profile = request.data.get('profile')
        
        if not token:
            return Response({'error': 'No token provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Verify the JWT token with Google
        try:
            # Use Google's tokeninfo endpoint to verify the token
            verify_response = requests.get(
                f'https://oauth2.googleapis.com/tokeninfo?id_token={token}'
            )
            
            if not verify_response.ok:
                return Response({
                    'error': 'Invalid token',
                    'details': verify_response.text
                }, status=status.HTTP_400_BAD_REQUEST)
            
            google_user = verify_response.json()
            
            # Verify the token was issued for our client
            if google_user.get('aud') != settings.GOOGLE_CLIENT_ID:
                return Response({'error': 'Token not issued for this client'}, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            return Response({
                'error': 'Token verification failed',
                'details': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Extract user information from verified token
        email = google_user.get('email')
        first_name = google_user.get('given_name', '')
        last_name = google_user.get('family_name', '')
        google_id = google_user.get('sub')  # 'sub' is the user ID in JWT
        picture_url = google_user.get('picture')
        
        if not email:
            return Response({'error': 'No email provided by Google'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Find or create user
        try:
            user = User.objects.get(email=email)
            # Update existing user with Google info if needed
            if not user.first_name and first_name:
                user.first_name = first_name
            if not user.last_name and last_name:
                user.last_name = last_name
            if not user.google_id:
                user.google_id = google_id
            user.save()
        except User.DoesNotExist:
            # Create new user
            # Generate a unique username from email
            username = email.split('@')[0]
            base_username = username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1
            
            # Generate a random password (user won't use it, they'll login via Google)
            random_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))
            
            user = User.objects.create_user(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                password=random_password,
                google_id=google_id
            )
            
            # Generate random profile stats
            import random
            user.viewed_profile = random.randint(0, 10000)
            user.impressions = random.randint(0, 10000)
            user.save()
            
            # Download and save profile picture if available
            if picture_url:
                try:
                    pic_response = requests.get(picture_url)
                    if pic_response.ok:
                        # Create a filename
                        pic_filename = f"profile_{user.id}_{google_id}.jpg"
                        user.picture.save(
                            pic_filename,
                            ContentFile(pic_response.content),
                            save=True
                        )
                except Exception as e:
                    print(f"Failed to download profile picture: {e}")
        
        # Generate JWT tokens for the user
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'user': UserSerializer(user).data,
            'tokens': {
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            },
            'message': 'Google OAuth successful'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'error': 'Internal server error',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([AllowAny])
def auth0_sync(request):
    """
    Create or update Django user from Auth0 user data
    """
    try:
        auth0_user_data = request.data.get('user', {})
        sub = auth0_user_data.get('sub')
        email = auth0_user_data.get('email')
        name = auth0_user_data.get('name')
        picture = auth0_user_data.get('picture')

        if not sub or not email:
            return Response({'error': 'Auth0 user ID (sub) and email are required.'}, status=status.HTTP_400_BAD_REQUEST)

        # Try to find user by auth0_id first, then by email
        user = User.objects.filter(auth0_id=sub).first()
        if not user:
            user = User.objects.filter(email=email).first()

        if user:
            # User exists, update their info
            user.auth0_id = sub # Ensure auth0_id is linked
            if name:
                name_parts = name.split(' ', 1)
                user.first_name = name_parts[0]
                user.last_name = name_parts[1] if len(name_parts) > 1 else ''
            if picture:
                 user.picture_path = picture
            user.save()
        else:
            # User does not exist, create a new one
            name_parts = name.split(' ', 1)
            first_name = name_parts[0]
            last_name = name_parts[1] if len(name_parts) > 1 else ''
            
            user = User.objects.create_user(
                username=email,
                email=email,
                first_name=first_name,
                last_name=last_name,
                auth0_id=sub,
                picture_path=picture,
                password=secrets.token_urlsafe(16)
            )
        
        # Generate JWT tokens for the user
        refresh = RefreshToken.for_user(user)
        tokens = {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }

        user_data = {
            '_id': user.pk,
            'firstName': user.first_name,
            'lastName': user.last_name,
            'email': user.email,
            'picturePath': user.picture_path,
        }

        return Response({
            'message': 'User synced successfully',
            'user': user_data,
            'tokens': tokens
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#making changes to post comments
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticatedOrReadOnly])
def post_comments(request, post_id):
    """
    Handle comments for a specific post
    """
    try:
        post = Post.objects.get(id=post_id)
    except Post.DoesNotExist:
        return Response({'error': 'Post not found'}, status=status.HTTP_404_NOT_FOUND)
    
    if request.method == 'GET':
        # Get all comments for this post
        comments = Comment.objects.filter(post=post).order_by('-created_at')
        serializer = CommentSerializer(comments, many=True)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        # Create a new comment for this post
        if not request.user.is_authenticated:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
        
        serializer = CommentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user, post=post)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_friend_request(request, user_id):
    """
    Send a friend request to another user
    """
    try:
        receiver = User.objects.get(id=user_id)
        sender = request.user
        
        # Can't send friend request to yourself
        if sender.id == receiver.id:
            return Response({'error': 'Cannot send friend request to yourself'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        # Check if they are already friends
        if sender.friends.filter(id=receiver.id).exists():
            return Response({'error': 'Already friends'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        # Check if friend request already exists
        existing_request = FriendRequest.objects.filter(
            sender=sender, receiver=receiver
        ).first()
        
        if existing_request:
            if existing_request.status == FriendRequest.PENDING:
                return Response({'error': 'Friend request already sent'}, 
                              status=status.HTTP_400_BAD_REQUEST)
            elif existing_request.status == FriendRequest.DECLINED:
                # Allow resending if previously declined
                existing_request.status = FriendRequest.PENDING
                existing_request.save()
            else:
                return Response({'error': 'Friend request already processed'}, 
                              status=status.HTTP_400_BAD_REQUEST)
        else:
            # Create new friend request
            existing_request = FriendRequest.objects.create(
                sender=sender,
                receiver=receiver,
                status=FriendRequest.PENDING
            )
        
        # Create notification for receiver
        notification = Notification.objects.create(
            user=receiver,
            type=Notification.FRIEND_REQUEST,
            message=f"{sender.first_name} {sender.last_name} sent you a friend request",
            friend_request=existing_request,
            from_user=sender
        )
        
        # Send real-time notification via WebSocket
        send_notification_websocket(receiver.id, notification)
        
        return Response({
            'message': 'Friend request sent successfully',
            'friend_request': FriendRequestSerializer(existing_request).data
        }, status=status.HTTP_201_CREATED)
        
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def respond_friend_request(request, request_id):
    """
    Accept or decline a friend request
    """
    try:
        friend_request = FriendRequest.objects.get(id=request_id, receiver=request.user)
        action = request.data.get('action')  # 'accept' or 'decline'
        
        if action not in ['accept', 'decline']:
            return Response({'error': 'Invalid action. Use "accept" or "decline"'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        if friend_request.status != FriendRequest.PENDING:
            return Response({
                'error': 'Friend request already processed',
                'status': friend_request.status,
                'message': f'This friend request has already been {friend_request.status.lower()}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if action == 'accept':
            friend_request.status = FriendRequest.ACCEPTED
            friend_request.save()
            
            # Add each other as friends
            friend_request.sender.friends.add(friend_request.receiver)
            friend_request.receiver.friends.add(friend_request.sender)
            
            # Mark related notification as read
            Notification.objects.filter(
                friend_request=friend_request,
                user=request.user,
                is_read=False
            ).update(is_read=True)
            
            # Create notification for sender
            notification = Notification.objects.create(
                user=friend_request.sender,
                type=Notification.FRIEND_ACCEPTED,
                message=f"{friend_request.receiver.first_name} {friend_request.receiver.last_name} accepted your friend request",
                from_user=friend_request.receiver
            )
            
            # Send real-time notification via WebSocket
            send_notification_websocket(friend_request.sender.id, notification)
            
            # Get updated friends list for the user who accepted the request
            friends = request.user.friends.all()
            friends_data = []
            for friend in friends:
                friends_data.append({
                    '_id': str(friend.id),
                    'id': friend.id,
                    'firstName': friend.first_name,
                    'lastName': friend.last_name,
                    'email': friend.email,
                    'picturePath': friend.picture_path,
                    'picture': friend.picture.url if friend.picture else None,
                    'occupation': getattr(friend, 'occupation', ''),
                    'location': getattr(friend, 'location', ''),
                    'friends': [],
                    'viewedProfile': getattr(friend, 'viewed_profile', 0),
                    'impressions': getattr(friend, 'impressions', 0),
                })
            
            return Response({
                'message': 'Friend request accepted',
                'friend_request': FriendRequestSerializer(friend_request).data,
                'friends': friends_data
            }, status=status.HTTP_200_OK)
            
        else:  # decline
            friend_request.status = FriendRequest.DECLINED
            friend_request.save()
            
            # Invalidate any related notifications for other users
            invalidate_friend_request_notifications(friend_request.id)
            
            # Mark related notification as read
            Notification.objects.filter(
                friend_request=friend_request,
                user=request.user,
                is_read=False
            ).update(is_read=True)
            
            return Response({
                'message': 'Friend request declined',
                'friend_request': FriendRequestSerializer(friend_request).data
            }, status=status.HTTP_200_OK)
            
    except FriendRequest.DoesNotExist:
        # Friend request was deleted or doesn't exist
        # Invalidate any related notifications
        try:
            # Find notifications that reference this request_id
            notifications = Notification.objects.filter(
                friend_request_id=request_id,
                type=Notification.FRIEND_REQUEST,
                is_read=False
            )
            
            for notification in notifications:
                # Send WebSocket message to notify that the friend request is invalid
                send_notification_websocket(notification.user.id, {
                    'type': 'friend_request_invalid',
                    'notification_id': notification.id,
                    'message': 'Friend request is no longer available'
                })
                
                # Mark notification as read
                notification.is_read = True
                notification.save()
                
        except Exception as e:
            print(f"Error handling deleted friend request notifications: {e}")
            
        return Response({'error': 'Friend request not found or already deleted'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def remove_friend(request, user_id):
    """
    Remove a friend from user's friend list
    """
    try:
        friend = User.objects.get(id=user_id)
        user = request.user
        
        # Check if they are actually friends
        if not user.friends.filter(id=friend.id).exists():
            return Response({'error': 'Not friends with this user'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        # Remove friendship (both ways)
        user.friends.remove(friend)
        friend.friends.remove(user)
        
        # Update any existing friend requests to declined
        FriendRequest.objects.filter(
            sender=user, receiver=friend, status=FriendRequest.ACCEPTED
        ).update(status=FriendRequest.DECLINED)
        
        FriendRequest.objects.filter(
            sender=friend, receiver=user, status=FriendRequest.ACCEPTED
        ).update(status=FriendRequest.DECLINED)
        
        # Get updated friends list
        friends = user.friends.all()
        friends_data = []
        for friend_obj in friends:
            friends_data.append({
                '_id': str(friend_obj.id),
                'id': friend_obj.id,
                'firstName': friend_obj.first_name,
                'lastName': friend_obj.last_name,
                'email': friend_obj.email,
                'picturePath': friend_obj.picture_path,
                'picture': friend_obj.picture.url if friend_obj.picture else None,
                'occupation': getattr(friend_obj, 'occupation', ''),
                'location': getattr(friend_obj, 'location', ''),
                'friends': [],
                'viewedProfile': getattr(friend_obj, 'viewed_profile', 0),
                'impressions': getattr(friend_obj, 'impressions', 0),
            })
        
        return Response({
            'message': 'Friend removed successfully',
            'friends': friends_data
        }, status=status.HTTP_200_OK)
        
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_notifications(request):
    """
    Get all notifications for the current user
    """
    notifications = Notification.objects.filter(user=request.user)
    unread_count = notifications.filter(is_read=False).count()
    
    serializer = NotificationSerializer(notifications, many=True)
    return Response({
        'notifications': serializer.data,
        'unread_count': unread_count
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_notification_read(request, notification_id):
    """
    Mark a notification as read
    """
    try:
        notification = Notification.objects.get(id=notification_id, user=request.user)
        notification.is_read = True
        notification.save()
        return Response({'message': 'Notification marked as read'})
    except Notification.DoesNotExist:
        return Response({'error': 'Notification not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_friend_requests(request):
    """
    Get all pending friend requests for the current user
    """
    received_requests = FriendRequest.objects.filter(
        receiver=request.user, 
        status=FriendRequest.PENDING
    )
    sent_requests = FriendRequest.objects.filter(
        sender=request.user, 
        status=FriendRequest.PENDING
    )
    
    return Response({
        'received_requests': FriendRequestSerializer(received_requests, many=True).data,
        'sent_requests': FriendRequestSerializer(sent_requests, many=True).data
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_friend_status(request, user_id):
    """
    Get the friendship status between current user and another user
    """
    try:
        other_user = User.objects.get(id=user_id)
        current_user = request.user
        
        # Check if they are friends
        if current_user.friends.filter(id=other_user.id).exists():
            return Response({'status': 'friends'})
        
        # Check for pending friend requests
        sent_request = FriendRequest.objects.filter(
            sender=current_user, 
            receiver=other_user, 
            status=FriendRequest.PENDING
        ).first()
        
        if sent_request:
            return Response({'status': 'request_sent'})
        
        received_request = FriendRequest.objects.filter(
            sender=other_user, 
            receiver=current_user, 
            status=FriendRequest.PENDING
        ).first()
        
        if received_request:
            return Response({
                'status': 'request_received',
                'friend_request_id': received_request.id
            })
        
        return Response({'status': 'not_friends'})
        
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_friends(request, user_id):
    """
    Get friends list for a specific user
    """
    try:
        user = User.objects.get(id=user_id)
        
        # For now, allow getting friends list for any user
        # You can add privacy checks here if needed
        friends = user.friends.all()
        
        # Return serialized friends data
        friends_data = []
        for friend in friends:
            friends_data.append({
                '_id': str(friend.id),
                'id': friend.id,
                'firstName': friend.first_name,
                'lastName': friend.last_name,
                'email': friend.email,
                'picturePath': friend.picture_path,
                'picture': friend.picture.url if friend.picture else None,
                'occupation': getattr(friend, 'occupation', ''),
                'location': getattr(friend, 'location', ''),
                'friends': [],  # Don't include nested friends to avoid recursion
                'viewedProfile': getattr(friend, 'viewed_profile', 0),
                'impressions': getattr(friend, 'impressions', 0),
            })
        
        return Response(friends_data, status=status.HTTP_200_OK)
        
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def clear_all_notifications(request):
    """
    Delete all notifications for the current user
    """
    try:
        # Delete all notifications for the current user
        deleted_count = Notification.objects.filter(user=request.user).count()
        Notification.objects.filter(user=request.user).delete()
        
        return Response({
            'message': f'All notifications cleared successfully',
            'deleted_count': deleted_count
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def search_posts(request):
    """Search posts by description content"""
    query = request.GET.get('q', '')
    
    if not query:
        return Response({'posts': []}, status=status.HTTP_200_OK)
    
    try:
        # Search posts by description
        posts = Post.objects.filter(
            Q(description__icontains=query)
        ).select_related('user').order_by('-created_at')[:20]  # Limit to 20 results
        
        # Serialize the posts
        posts_data = []
        for post in posts:
            # Get likes safely
            likes_dict = {}
            for like in post.likes.all():
                likes_dict[str(like.id)] = True
            
            # Get comments safely
            comments_list = []
            for comment in post.comments.all():
                comments_list.append({
                    'id': comment.id,
                    'userId': comment.user.id,
                    'firstName': comment.user.first_name,
                    'lastName': comment.user.last_name,
                    'text': comment.comment,  # The field is called 'comment', not 'text'
                    'createdAt': comment.created_at.isoformat(),
                    'userPicturePath': getattr(comment.user, 'picture_path', '')
                })
            
            posts_data.append({
                '_id': post.id,
                'userId': post.user.id,
                'firstName': post.user.first_name,
                'lastName': post.user.last_name,
                'description': post.description,
                'location': getattr(post.user, 'location', ''),
                'picturePath': post.picture.url if post.picture else (post.picture_path or ''),
                'userPicturePath': post.user.picture.url if post.user.picture else (getattr(post.user, 'picture_path', '') or ''),
                'likes': likes_dict,
                'comments': comments_list,
                'createdAt': post.created_at.isoformat(),
                'updatedAt': post.updated_at.isoformat()
            })
        
        return Response({'posts': posts_data}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error': str(e), 'posts': []}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def search_users(request):
    """Search users by first name, last name, or email"""
    query = request.GET.get('q', '')
    
    if not query:
        return Response({'users': []}, status=status.HTTP_200_OK)
    
    try:
        # Search users by first name, last name, or email
        users = User.objects.filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(email__icontains=query)
        ).exclude(id=request.user.id).order_by('first_name', 'last_name')[:20]  # Limit to 20 results, exclude current user
        
        # Serialize the users
        users_data = []
        for user in users:
            users_data.append({
                '_id': user.id,
                'firstName': user.first_name,
                'lastName': user.last_name,
                'email': user.email,
                'location': getattr(user, 'location', ''),
                'occupation': getattr(user, 'occupation', ''),
                'picturePath': user.picture_path,
                'viewedProfile': getattr(user, 'viewed_profile', 0),
                'impressions': getattr(user, 'impressions', 0),
                'createdAt': user.date_joined.isoformat() if hasattr(user, 'date_joined') else None,
            })
        
        return Response({'users': users_data}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error': str(e), 'users': []}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def cancel_friend_request(request, request_id):
    """
    Cancel a friend request that was sent by the current user
    """
    try:
        friend_request = FriendRequest.objects.get(id=request_id, sender=request.user)
        
        if friend_request.status != FriendRequest.PENDING:
            return Response({
                'error': 'Friend request already processed',
                'status': friend_request.status,
                'message': f'This friend request has already been {friend_request.status.lower()}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Invalidate any related notifications for other users
        invalidate_friend_request_notifications(friend_request.id)
        
        # Delete the friend request
        friend_request.delete()
        
        return Response({
            'message': 'Friend request cancelled successfully'
        }, status=status.HTTP_200_OK)
        
    except FriendRequest.DoesNotExist:
        return Response({'error': 'Friend request not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# DM/Messaging Views
class ConversationViewSet(viewsets.ModelViewSet):
    serializer_class = ConversationSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None  # Disable pagination
    
    def get_queryset(self):
        return Conversation.objects.filter(participants=self.request.user).order_by('-updated_at')
    
    def create(self, request, *args, **kwargs):
        """Create a new conversation with another user"""
        other_user_id = request.data.get('other_user_id')
        
        if not other_user_id:
            return Response({'error': 'other_user_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            other_user = User.objects.get(id=other_user_id)
            
            # Check if users are friends
            if not are_friends(request.user, other_user):
                return Response({'error': 'You can only message friends'}, status=status.HTTP_403_FORBIDDEN)
            
            # Check if conversation already exists
            existing_conversation = Conversation.objects.filter(
                participants=request.user
            ).filter(
                participants=other_user
            ).first()
            
            if existing_conversation:
                serializer = self.get_serializer(existing_conversation)
                return Response(serializer.data)
            
            # Create new conversation
            conversation = Conversation.objects.create()
            conversation.participants.set([request.user, other_user])
            
            serializer = self.get_serializer(conversation)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)


class MessageViewSet(viewsets.ModelViewSet):
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    pagination_class = None  # Disable pagination for messages
    
    def get_queryset(self):
        conversation_id = self.kwargs.get('conversation_pk')
        
        if not conversation_id:
            return Message.objects.none()

        # Ensure user is participant in conversation
        if not self.request.user.conversations.filter(id=conversation_id).exists():
            return Message.objects.none()
            
        return Message.objects.filter(
            conversation_id=conversation_id, 
            is_deleted=False
        ).order_by('created_at')  # Ascending order - oldest first, newest last
    
    def perform_create(self, serializer):
        conversation_id = self.kwargs.get('conversation_pk')
        try:
            print(f"[API] Creating message via REST: user={self.request.user.id}, conversation={conversation_id}")
            
            conversation = Conversation.objects.get(
                id=conversation_id, 
                participants=self.request.user
            )
            
            print(f"[API] Found conversation: {conversation.id}, participants: {[p.id for p in conversation.participants.all()]}")
            
            # Check if users are friends
            other_participant = conversation.get_other_participant(self.request.user)
            print(f"[API] Other participant: {other_participant.id if other_participant else 'None'}")
            
            if not are_friends(self.request.user, other_participant):
                print(f"[API] Error: Users are not friends: {self.request.user.id} and {other_participant.id if other_participant else 'None'}")
                raise serializers.ValidationError("You can only message friends.")

            message = serializer.save(sender=self.request.user, conversation=conversation)
            print(f"[API] Message created successfully: {message.id}")
            
            # Update conversation timestamp
            conversation.updated_at = timezone.now()
            conversation.save()

            # Broadcast message via WebSocket
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync
            
            channel_layer = get_channel_layer()
            if channel_layer:
                # Serialize the message with proper context
                message_serializer = MessageSerializer(message, context={'request': self.request})
                message_data = message_serializer.data
                
                # Send to WebSocket group
                async_to_sync(channel_layer.group_send)(
                    f'conversation_{conversation_id}',
                    {
                        'type': 'new_message',
                        'message': message_data
                    }
                )
                print(f"[API] Message {message.id} broadcasted to WebSocket group conversation_{conversation_id}")

        except Conversation.DoesNotExist:
            print(f"[API] Error: Conversation {conversation_id} not found or user {self.request.user.id} is not a participant")
            raise serializers.ValidationError("Conversation not found or you are not a participant.")
        except Exception as e:
            print(f"[API] Error in perform_create: {e}")
            import traceback
            traceback.print_exc()
            raise

    def create(self, request, *args, **kwargs):
        """Create a new message in a conversation"""
        content = request.data.get('content', '').strip()
        image = request.FILES.get('image')

        if not content and not image:
            return Response({'error': 'Message must have content or an image.'}, status=status.HTTP_400_BAD_REQUEST)
        
        return super().create(request, *args, **kwargs)
    
    def update(self, request, *args, **kwargs):
        """Edit a message (only sender can edit)"""
        message = self.get_object()
        
        if message.sender != request.user:
            return Response({'error': 'You can only edit your own messages'}, status=status.HTTP_403_FORBIDDEN)
        
        content = request.data.get('content', '').strip()
        if not content:
            return Response({'error': 'Message content cannot be empty'}, status=status.HTTP_400_BAD_REQUEST)
        
        message.content = content
        message.is_edited = True
        message.save()
        
        serializer = self.get_serializer(message)
        
        # Broadcast edit via WebSocket
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        
        channel_layer = get_channel_layer()
        if channel_layer:
            conversation_id = self.kwargs.get('conversation_pk')
            async_to_sync(channel_layer.group_send)(
                f'conversation_{conversation_id}',
                {
                    'type': 'message_edited',
                    'message': serializer.data
                }
            )
            print(f"[API] Message {message.id} edit broadcasted to WebSocket group conversation_{conversation_id}")
        
        return Response(serializer.data)
    
    def destroy(self, request, *args, **kwargs):
        """Delete a message (only sender can delete)"""
        message = self.get_object()
        
        if message.sender != request.user:
            return Response({'error': 'You can only delete your own messages'}, status=status.HTTP_403_FORBIDDEN)
        
        message_id = message.id
        message.is_deleted = True
        message.save()
        
        # Broadcast delete via WebSocket
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        
        channel_layer = get_channel_layer()
        if channel_layer:
            conversation_id = self.kwargs.get('conversation_pk')
            async_to_sync(channel_layer.group_send)(
                f'conversation_{conversation_id}',
                {
                    'type': 'message_deleted',
                    'message_id': message_id
                }
            )
            print(f"[API] Message {message_id} deletion broadcasted to WebSocket group conversation_{conversation_id}")
        
        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_messages_as_read(request, conversation_pk):
    """Mark messages in a conversation as read"""
    try:
        conversation = Conversation.objects.get(
            id=conversation_pk,
            participants=request.user
        )
        
        # Get unread messages (excluding user's own messages)
        unread_messages = conversation.messages.exclude(
            sender=request.user
        ).exclude(
            read_statuses__user=request.user
        ).filter(is_deleted=False)
        
        # Mark as read
        for message in unread_messages:
            MessageReadStatus.objects.get_or_create(
                message=message,
                user=request.user
            )
        
        return Response({'success': True, 'marked_count': unread_messages.count()})
        
    except Conversation.DoesNotExist:
        return Response({'error': 'Conversation not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def debug_conversations(request):
    """Debug endpoint to check conversations data"""
    try:
        # Get all conversations for user
        conversations = Conversation.objects.filter(participants=request.user).order_by('-updated_at')
        
        debug_data = {
            'user_id': request.user.id,
            'user_name': f"{request.user.first_name} {request.user.last_name}",
            'total_conversations': conversations.count(),
            'conversations': []
        }
        
        for conv in conversations:
            participants = conv.participants.all()
            messages = conv.messages.filter(is_deleted=False).order_by('-created_at')[:5]  # Last 5 messages
            
            conv_data = {
                'id': conv.id,
                'created_at': conv.created_at.isoformat(),
                'updated_at': conv.updated_at.isoformat(),
                'participants': [
                    {
                        'id': p.id,
                        'name': f"{p.first_name} {p.last_name}",
                        'email': p.email
                    } for p in participants
                ],
                'message_count': messages.count(),
                'recent_messages': [
                    {
                        'id': msg.id,
                        'content': msg.content,
                        'sender_id': msg.sender.id,
                        'sender_name': f"{msg.sender.first_name} {msg.sender.last_name}",
                        'created_at': msg.created_at.isoformat(),
                        'has_image': bool(msg.image)
                    } for msg in messages
                ]
            }
            debug_data['conversations'].append(conv_data)
        
        return Response(debug_data)
        
    except Exception as e:
        return Response({
            'error': str(e),
            'user_id': request.user.id if request.user else None
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def debug_friends(request):
    """Debug endpoint to check friends data"""
    try:
        user = request.user
        friends = user.friends.all()
        
        debug_data = {
            'user_id': user.id,
            'user_name': f"{user.first_name} {user.last_name}",
            'friends_count': friends.count(),
            'friends': [
                {
                    'id': friend.id,
                    'name': f"{friend.first_name} {friend.last_name}",
                    'email': friend.email
                } for friend in friends
            ]
        }
        
        return Response(debug_data)
        
    except Exception as e:
        return Response({
            'error': str(e),
            'user_id': request.user.id if request.user else None
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_test_conversation(request):
    """Debug endpoint to create a test conversation with a friend"""
    try:
        friend_id = request.data.get('friend_id')
        if not friend_id:
            return Response({'error': 'friend_id required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            friend = User.objects.get(id=friend_id)
        except User.DoesNotExist:
            return Response({'error': 'Friend not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Check if they are friends
        if not are_friends(request.user, friend):
            return Response({'error': 'You are not friends with this user'}, status=status.HTTP_403_FORBIDDEN)
        
        # Check if conversation already exists
        existing_conversation = Conversation.objects.filter(
            participants=request.user
        ).filter(
            participants=friend
        ).first()
        
        if existing_conversation:
            return Response({
                'message': 'Conversation already exists',
                'conversation_id': existing_conversation.id
            })
        
        # Create new conversation
        conversation = Conversation.objects.create()
        conversation.participants.set([request.user, friend])
        
        # Create a test message
        test_message = Message.objects.create(
            conversation=conversation,
            sender=request.user,
            content="Hello! This is a test message."
        )
        
        conversation.updated_at = timezone.now()
        conversation.save()
        
        return Response({
            'message': 'Test conversation created successfully',
            'conversation_id': conversation.id,
            'test_message_id': test_message.id
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response({
            'error': str(e),
            'user_id': request.user.id if request.user else None
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

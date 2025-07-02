from django.shortcuts import render
from rest_framework import generics, status, viewsets
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAuthenticatedOrReadOnly
from django.contrib.auth import get_user_model, authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from .models import Post, Comment, User
from .serializers import UserSerializer, PostSerializer, CommentSerializer
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
            
        return Response({
            'liked': liked,
            'likes_count': post.likes.count()
        })

    def perform_update(self, serializer):
        # Ensure user can only update their own posts
        if serializer.instance.user != self.request.user:
            return Response({'error': 'You can only update your own posts'}, status=403)
        serializer.save()

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
        serializer.save(user=self.request.user, post=post)

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

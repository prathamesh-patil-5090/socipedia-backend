from django.shortcuts import render
from rest_framework import generics, status, viewsets
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth import get_user_model, authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from .models import Post, Comment, User
from .serializers import UserSerializer, PostSerializer, CommentSerializer
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.http import HttpResponse, Http404
from django.conf import settings
import os
from rest_framework.decorators import api_view, permission_classes

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
        username = request.data.get("username")
        password = request.data.get("password")
        user = authenticate(username=username, password=password)
        if user:
            refresh = RefreshToken.for_user(user)
            return Response({
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
    parser_classes = [MultiPartParser, FormParser]

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
        user = self.get_object()
        friend_id = request.data.get('friend_id')
        friend = User.objects.get(id=friend_id)
        user.friends.add(friend)
        return Response({'status': 'friend added'})

    @action(detail=True, methods=['post'])
    def remove_friend(self, request, pk=None):
        user = self.get_object()
        friend_id = request.data.get('friend_id')
        friend = User.objects.get(id=friend_id)
        user.friends.remove(friend)
        return Response({'status': 'friend removed'})

class PostListView(generics.ListCreateAPIView):
    queryset = Post.objects.all()
    serializer_class = PostSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class PostDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Post.objects.all()
    serializer_class = PostSerializer
    permission_classes = [IsAuthenticated]

class PostViewSet(viewsets.ModelViewSet):
    queryset = Post.objects.all()
    serializer_class = PostSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'])
    def like(self, request, pk=None):
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
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        post = Post.objects.get(id=self.kwargs['post_id'])
        serializer.save(user=self.request.user, post=post)

class CommentDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated]

class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def perform_create(self, serializer):
        post = Post.objects.get(id=self.request.data.get('post_id'))
        serializer.save(user=self.request.user, post=post)

    @action(detail=True, methods=['post'])
    def like(self, request, pk=None):
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

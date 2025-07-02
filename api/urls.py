from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserViewSet, PostViewSet, CommentViewSet, RegisterView, LoginView, serve_image, google_oauth_callback, auth0_sync, post_comments

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'posts', PostViewSet, basename='post')
router.register(r'comments', CommentViewSet, basename='comment')

urlpatterns = [
    path('', include(router.urls)),
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('auth/google/callback/', google_oauth_callback, name='google_oauth_callback'),
    path('auth/auth0/sync/', auth0_sync, name='auth0_sync'),
    path('posts/<int:post_id>/comments/', post_comments, name='post_comments'),
    path('images/<path:path>', serve_image, name='serve_image'),
]

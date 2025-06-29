from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserViewSet, PostViewSet, CommentViewSet, RegisterView, LoginView, serve_image

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'posts', PostViewSet, basename='post')
router.register(r'comments', CommentViewSet, basename='comment')

urlpatterns = [
    path('', include(router.urls)),
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('images/<path:path>', serve_image, name='serve_image'),
]

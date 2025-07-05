from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UserViewSet, PostViewSet, CommentViewSet, RegisterView, LoginView, 
    serve_image, google_oauth_callback, auth0_sync, post_comments,
    send_friend_request, respond_friend_request, remove_friend, cancel_friend_request,
    get_notifications, mark_notification_read, get_friend_requests, get_friend_status,
    get_user_friends, clear_all_notifications, search_posts, search_users,
    ConversationViewSet, MessageViewSet, mark_messages_as_read,
    debug_conversations, debug_friends, create_test_conversation
)

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'posts', PostViewSet, basename='post')
router.register(r'comments', CommentViewSet, basename='comment')
router.register(r'conversations', ConversationViewSet, basename='conversation')

urlpatterns = [
    # Search endpoints (must come before router URLs)
    path('posts/search/', search_posts, name='search_posts'),
    path('users/search/', search_users, name='search_users'),
    
    # Router URLs
    path('', include(router.urls)),
    
    # Other endpoints
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('auth/google/callback/', google_oauth_callback, name='google_oauth_callback'),
    path('auth/auth0/sync/', auth0_sync, name='auth0_sync'),
    path('posts/<int:post_id>/comments/', post_comments, name='post_comments'),
    path('images/<path:path>', serve_image, name='serve_image'),
    
    # Friend request endpoints
    path('friend-request/send/<int:user_id>/', send_friend_request, name='send_friend_request'),
    path('friend-request/respond/<int:request_id>/', respond_friend_request, name='respond_friend_request'),
    path('friend-request/cancel/<int:request_id>/', cancel_friend_request, name='cancel_friend_request'),
    path('friend/remove/<int:user_id>/', remove_friend, name='remove_friend'),
    path('friend-requests/', get_friend_requests, name='get_friend_requests'),
    path('friend-status/<int:user_id>/', get_friend_status, name='get_friend_status'),
    path('users/<int:user_id>/friends/', get_user_friends, name='get_user_friends'),
    
    # Notification endpoints
    path('notifications/', get_notifications, name='get_notifications'),
    path('notifications/<int:notification_id>/read/', mark_notification_read, name='mark_notification_read'),
    path('notifications/clear/', clear_all_notifications, name='clear_all_notifications'),
    
    # DM endpoints
    path('conversations/<int:conversation_pk>/messages/', MessageViewSet.as_view({
        'get': 'list',
        'post': 'create'
    }), name='conversation_messages'),
    path('conversations/<int:conversation_pk>/messages/<int:pk>/', MessageViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    }), name='message_detail'),
    path('conversations/<int:conversation_pk>/mark-read/', mark_messages_as_read, name='mark_messages_as_read'),
    
    # Debug endpoints
    path('debug/conversations/', debug_conversations, name='debug_conversations'),
    path('debug/friends/', debug_friends, name='debug_friends'),
    path('debug/create-test-conversation/', create_test_conversation, name='create_test_conversation'),
]

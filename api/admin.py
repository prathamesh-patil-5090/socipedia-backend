from django.contrib import admin
from .models import User, Post, Comment, FriendRequest, Notification, Conversation, Message, MessageReadStatus

# Register your models here.
@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['username', 'email', 'first_name', 'last_name', 'is_staff']
    search_fields = ['username', 'email', 'first_name', 'last_name']

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ['user', 'description', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username', 'description']

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ['user', 'post', 'comment', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username', 'comment']

@admin.register(FriendRequest)
class FriendRequestAdmin(admin.ModelAdmin):
    list_display = ['sender', 'receiver', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['sender__username', 'receiver__username']

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'type', 'message', 'is_read', 'created_at']
    list_filter = ['type', 'is_read', 'created_at']
    search_fields = ['user__username', 'message']

@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ['id', 'created_at', 'updated_at']
    list_filter = ['created_at', 'updated_at']
    filter_horizontal = ['participants']

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['sender', 'conversation', 'content', 'is_edited', 'is_deleted', 'created_at']
    list_filter = ['is_edited', 'is_deleted', 'created_at']
    search_fields = ['sender__username', 'content']

@admin.register(MessageReadStatus)
class MessageReadStatusAdmin(admin.ModelAdmin):
    list_display = ['user', 'message', 'read_at']
    list_filter = ['read_at']
    search_fields = ['user__username']

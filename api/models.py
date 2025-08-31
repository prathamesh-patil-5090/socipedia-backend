from django.contrib.auth.models import AbstractUser
from django.db import models
from PIL import Image
from io import BytesIO
from django.core.files.base import ContentFile
import os

def compress_image(image_field, quality=85, max_width=1200, max_height=1200):
    """
    Compress image while maintaining aspect ratio
    """
    if not image_field:
        return None
    
    try:
        # Open the image
        img = Image.open(image_field)
        original_size = image_field.size if hasattr(image_field, 'size') else 0
        
        print(f"Compressing image: {img.width}x{img.height}, original size: {original_size} bytes")
        
        # Convert RGBA to RGB if necessary (for JPEG compatibility)
        if img.mode in ('RGBA', 'LA', 'P'):
            # Create a white background
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = background
        
        # Resize image if it's too large
        if img.width > max_width or img.height > max_height:
            print(f"Resizing from {img.width}x{img.height} to max {max_width}x{max_height}")
            img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
            print(f"New size: {img.width}x{img.height}")
        
        # Save compressed image to BytesIO
        output = BytesIO()
        
        # Determine format
        format = 'JPEG'
        original_name = image_field.name if hasattr(image_field, 'name') else 'compressed_image.jpg'
        
        if original_name.lower().endswith('.png'):
            format = 'PNG'
            img.save(output, format=format, optimize=True)
        else:
            img.save(output, format=format, quality=quality, optimize=True)
        
        compressed_size = len(output.getvalue())
        print(f"Compressed size: {compressed_size} bytes")
        
        output.seek(0)
        
        # Get original filename
        name, ext = os.path.splitext(original_name)
        
        # Ensure proper extension
        if format == 'JPEG' and ext.lower() not in ['.jpg', '.jpeg']:
            original_name = f"{name}.jpg"
        elif format == 'PNG' and ext.lower() != '.png':
            original_name = f"{name}.png"
        
        return ContentFile(output.getvalue(), name=original_name)
    
    except Exception as e:
        print(f"Image compression failed: {e}")
        return image_field

def user_profile_path(instance, filename):
    # Save in public/assets like Express backend
    return f'{instance.username}_{filename}'

def post_image_path(instance, filename):
    # Save in public/assets like Express backend  
    return f'{instance.user.username}_{filename}'

def message_image_path(instance, filename):
    # Save message images in public/assets like other images
    return f'message_{instance.conversation.id}_{filename}'

class User(AbstractUser):
    picture = models.ImageField(upload_to=user_profile_path, blank=True, null=True)
    picture_path = models.CharField(max_length=255, blank=True, default="")  # Keep for compatibility
    friends = models.ManyToManyField("self", blank=True)
    viewed_profile = models.IntegerField(default=0)
    impressions = models.IntegerField(default=0)
    google_id = models.CharField(max_length=255, blank=True, null=True, unique=True)
    auth0_id = models.CharField(max_length=255, blank=True, null=True, unique=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    def save(self, *args, **kwargs):
        # Compress profile picture before saving
        if self.picture and hasattr(self.picture, 'file'):
            # Check if this is a new upload
            if not self.pk or (self.pk and self._state.adding):
                print("Compressing profile picture...")
                compressed_image = compress_image(self.picture, quality=85, max_width=800, max_height=800)
                if compressed_image:
                    self.picture = compressed_image
        
        # Update picture_path when picture is uploaded
        if self.picture:
            self.picture_path = self.picture.url
        super().save(*args, **kwargs)

class Post(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts')
    description = models.TextField(blank=True)
    picture = models.ImageField(upload_to=post_image_path, blank=True, null=True)
    picture_path = models.CharField(max_length=255, blank=True, default="")  # Keep for compatibility
    likes = models.ManyToManyField(User, related_name='liked_posts', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Post by {self.user.username} at {self.created_at}"

    def save(self, *args, **kwargs):
        # Compress post picture before saving
        if self.picture and hasattr(self.picture, 'file'):
            # Check if this is a new upload
            if not self.pk or (self.pk and self._state.adding):
                print("Compressing post picture...")
                compressed_image = compress_image(self.picture, quality=80, max_width=1200, max_height=1200)
                if compressed_image:
                    self.picture = compressed_image
        
        # Update picture_path when picture is uploaded
        if self.picture:
            self.picture_path = self.picture.url
        super().save(*args, **kwargs)

class Comment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    comment = models.TextField()
    likes = models.ManyToManyField(User, related_name='liked_comments', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comment by {self.user.username} on {self.post}"

class FriendRequest(models.Model):
    PENDING = 'pending'
    ACCEPTED = 'accepted'
    DECLINED = 'declined'
    
    STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (ACCEPTED, 'Accepted'),
        (DECLINED, 'Declined'),
    ]
    
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_friend_requests')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_friend_requests')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('sender', 'receiver')
    
    def __str__(self):
        return f"Friend request from {self.sender.username} to {self.receiver.username} - {self.status}"

class Notification(models.Model):
    FRIEND_REQUEST = 'friend_request'
    FRIEND_ACCEPTED = 'friend_accepted'
    POST_LIKE = 'post_like'
    POST_COMMENT = 'post_comment'
    
    TYPE_CHOICES = [
        (FRIEND_REQUEST, 'Friend Request'),
        (FRIEND_ACCEPTED, 'Friend Accepted'),
        (POST_LIKE, 'Post Like'),
        (POST_COMMENT, 'Post Comment'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    message = models.CharField(max_length=255)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Optional foreign keys for different notification types
    friend_request = models.ForeignKey(FriendRequest, on_delete=models.CASCADE, null=True, blank=True)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, null=True, blank=True)
    from_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_notifications', null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Notification for {self.user.username}: {self.message}"

class Conversation(models.Model):
    participants = models.ManyToManyField(User, related_name='conversations')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-updated_at']
    
    def __str__(self):
        participant_names = ", ".join([user.username for user in self.participants.all()])
        return f"Conversation between: {participant_names}"
    
    def get_other_participant(self, user):
        """Get the other participant in a 2-person conversation"""
        return self.participants.exclude(id=user.id).first()

class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    content = models.TextField(blank=True)  # Text content, can be empty if image-only
    image = models.ImageField(upload_to=message_image_path, blank=True, null=True)
    is_edited = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        content_preview = self.content[:50] if self.content else "[Image]" if self.image else "[Deleted]"
        return f"Message from {self.sender.username}: {content_preview}"
    
    def save(self, *args, **kwargs):
        # Compress message image before saving
        if self.image and hasattr(self.image, 'file'):
            # Check if this is a new upload
            if not self.pk or (self.pk and self._state.adding):
                print("Compressing message image...")
                compressed_image = compress_image(self.image, quality=80, max_width=1200, max_height=1200)
                if compressed_image:
                    self.image = compressed_image
        
        # Update conversation's updated_at when message is saved
        super().save(*args, **kwargs)
        self.conversation.save()  # This will update the conversation's updated_at field

class MessageReadStatus(models.Model):
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='read_statuses')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='message_read_statuses')
    read_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('message', 'user')
    
    def __str__(self):
        return f"{self.user.username} read message {self.message.id} at {self.read_at}"

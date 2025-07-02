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

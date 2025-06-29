from django.contrib.auth.models import AbstractUser
from django.db import models

def user_profile_path(instance, filename):
    return f'profile_pictures/{instance.username}_{filename}'

def post_image_path(instance, filename):
    return f'post_images/{instance.user.username}_{filename}'

class User(AbstractUser):
    picture = models.ImageField(upload_to=user_profile_path, blank=True, null=True)
    picture_path = models.CharField(max_length=255, blank=True, default="")  # Keep for compatibility
    friends = models.ManyToManyField("self", blank=True)
    location = models.CharField(max_length=100, blank=True)
    occupation = models.CharField(max_length=100, blank=True)
    viewed_profile = models.IntegerField(default=0)
    impressions = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    def save(self, *args, **kwargs):
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

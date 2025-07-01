from rest_framework import serializers
from .models import User, Post, Comment

class SimpleUserSerializer(serializers.ModelSerializer):
    """Simplified user serializer for use in posts/comments to avoid circular dependencies"""
    _id = serializers.CharField(source='id', read_only=True)
    firstName = serializers.CharField(source='first_name', read_only=True)
    lastName = serializers.CharField(source='last_name', read_only=True)
    picturePath = serializers.CharField(source='picture_path', read_only=True)
    
    class Meta:
        model = User
        fields = ["_id", "id", "firstName", "lastName", "picturePath"]

class UserSerializer(serializers.ModelSerializer):
    # Map Django fields to frontend expected fields
    _id = serializers.CharField(source='id', read_only=True)
    firstName = serializers.CharField(source='first_name')
    lastName = serializers.CharField(source='last_name')
    picturePath = serializers.CharField(source='picture_path', read_only=True)
    viewedProfile = serializers.IntegerField(source='viewed_profile', read_only=True)
    friends = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ["_id", "id", "firstName", "lastName", "first_name", "last_name", "email", "username", "password", "picture", "picturePath", "picture_path", "friends", "viewedProfile", "viewed_profile", "impressions"]
        extra_kwargs = {'password': {'write_only': True}}

    def get_friends(self, obj):
        # Return friends in the format expected by frontend
        friends_data = []
        for friend in obj.friends.all():
            friends_data.append({
                '_id': str(friend.id),
                'id': friend.id,
                'firstName': friend.first_name,
                'lastName': friend.last_name,
                'picturePath': friend.picture_path or "",
            })
        return friends_data

    def create(self, validated_data):
        password = validated_data.pop('password')
        friends = validated_data.pop('friends', [])
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        if friends:
            user.friends.set(friends)
        return user

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Ensure both formats are available
        data['_id'] = str(instance.id)
        data['firstName'] = instance.first_name
        data['lastName'] = instance.last_name
        # Use the actual picture filename from the uploaded file
        data['picturePath'] = instance.picture.name if instance.picture else ""
        data['viewedProfile'] = instance.viewed_profile
        return data

class CommentSerializer(serializers.ModelSerializer):
    user = SimpleUserSerializer(read_only=True)
    _id = serializers.CharField(source='id', read_only=True)
    createdAt = serializers.DateTimeField(source='created_at', read_only=True)
    likes_count = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = ["_id", "id", "user", "post", "comment", "likes", "likes_count", "createdAt", "created_at"]
        read_only_fields = ["post"]

    def get_likes_count(self, obj):
        return obj.likes.count()

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['_id'] = str(instance.id)
        data['createdAt'] = instance.created_at
        # Convert likes from ManyToMany to dict format for frontend compatibility
        likes_dict = {}
        for like_user in instance.likes.all():
            likes_dict[str(like_user.id)] = True
        data['likes'] = likes_dict
        return data

class PostSerializer(serializers.ModelSerializer):
    user = SimpleUserSerializer(read_only=True)

    class Meta:
        model = Post
        fields = ["id", "user", "description", "picture", "picture_path", "likes", "created_at", "updated_at"]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        
        # Add frontend-expected fields
        data['_id'] = str(instance.id)
        data['userId'] = str(instance.user.id)
        data['firstName'] = instance.user.first_name
        data['lastName'] = instance.user.last_name
        # Use the actual picture filename from the uploaded file
        data['picturePath'] = instance.picture.name if instance.picture else ""
        data['userPicturePath'] = instance.user.picture.name if instance.user.picture else ""
        data['createdAt'] = instance.created_at.isoformat()
        data['updatedAt'] = instance.updated_at.isoformat()
        
        # Convert likes to the format expected by frontend
        likes_dict = {}
        for user in instance.likes.all():
            likes_dict[str(user.id)] = True
        data['likes'] = likes_dict
        
        # Get comments using CommentSerializer (newest first)
        comments_data = []
        for comment in instance.comments.all().order_by('-created_at'):
            comment_serializer = CommentSerializer(comment)
            comments_data.append(comment_serializer.data)
        data['comments'] = comments_data
        
        return data

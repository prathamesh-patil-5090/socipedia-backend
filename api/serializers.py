from rest_framework import serializers
from .models import User, Post, Comment, FriendRequest, Notification, Conversation, Message, MessageReadStatus, Message, Conversation, MessageReadStatus
import sys
import os
# Add the correct path to your combined_model directory
combined_model_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'combined_model', 'combined_model')
sys.path.append(combined_model_path)

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

    def validate(self, data):
        """
        Validate comment content for toxicity and sentiment
        """
        comment_text = data.get('comment', '').strip()
        
        if not comment_text:
            raise serializers.ValidationError({
                "comment": "Comment cannot be empty."
            })
        
        # Check content toxicity
        try:
            # Try to import and use the toxicity detection
            import infer
            should_block, reason, details = infer.should_block_content(comment_text)
            
            if should_block:
                # Raise validation error to block the comment
                raise serializers.ValidationError({
                    "comment": reason,
                    "sentiment_analysis": {
                        "negative": details['sentiment']['negative'],
                        "positive": details['sentiment']['positive']
                    },
                    "toxicity_detected": details['primary_issue'],
                    "confidence": details['confidence']
                })
                
        except serializers.ValidationError:
            # Re-raise validation errors (don't catch our own validation errors)
            raise
        except ImportError as e:
            # If model is not available, log warning but don't block
            import logging
            logging.warning(f"Toxicity detection model not available for comment: {str(e)}")
        except Exception as e:
            # Log error but don't block comment creation for other errors
            import logging
            logging.error(f"Error in toxicity detection for comment: {str(e)}")
        
        return data

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

    def validate(self, data):
        """
        Ensure that either description or picture is provided and validate content
        """
        description = data.get('description', '').strip()
        picture = data.get('picture')
        
        if not description and not picture:
            raise serializers.ValidationError(
                "Either description or picture must be provided."
            )
        
        # Check content toxicity if description is provided
        if description:
            try:
                # Try to import and use the toxicity detection
                import infer
                should_block, reason, details = infer.should_block_content(description)
                
                if should_block:
                    # Raise validation error to block the post
                    raise serializers.ValidationError({
                        "description": reason,
                        "sentiment_analysis": {
                            "negative": details['sentiment']['negative'],
                            "positive": details['sentiment']['positive']
                        },
                        "toxicity_detected": details['primary_issue'],
                        "confidence": details['confidence']
                    })
                    
            except serializers.ValidationError:
                # Re-raise validation errors (don't catch our own validation errors)
                raise
            except ImportError as e:
                # If model is not available, log warning but don't block
                import logging
                logging.warning(f"Toxicity detection model not available: {str(e)}")
            except Exception as e:
                # Log error but don't block post creation for other errors
                import logging
                logging.error(f"Error in toxicity detection: {str(e)}")
        
        return data

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

class FriendRequestSerializer(serializers.ModelSerializer):
    sender = SimpleUserSerializer(read_only=True)
    receiver = SimpleUserSerializer(read_only=True)
    sender_id = serializers.IntegerField(write_only=True)
    receiver_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = FriendRequest
        fields = ['id', 'sender', 'receiver', 'sender_id', 'receiver_id', 'status', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

class NotificationSerializer(serializers.ModelSerializer):
    from_user = SimpleUserSerializer(read_only=True)
    friend_request = FriendRequestSerializer(read_only=True)
    
    class Meta:
        model = Notification
        fields = ['id', 'type', 'message', 'is_read', 'created_at', 'friend_request', 'post', 'from_user']
        read_only_fields = ['id', 'created_at']

class MessageSerializer(serializers.ModelSerializer):
    sender = SimpleUserSerializer(read_only=True)
    image_url = serializers.SerializerMethodField()
    read_by = serializers.SerializerMethodField()
    
    class Meta:
        model = Message
        fields = [
            'id', 'conversation', 'sender', 'content', 'image', 
            'image_url', 'is_edited', 'is_deleted', 'created_at', 
            'updated_at', 'read_by'
        ]
        read_only_fields = ['id', 'conversation', 'sender', 'created_at', 'updated_at', 'is_edited', 'is_deleted']
    
    def get_image_url(self, obj):
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None
    
    def get_read_by(self, obj):
        """Get list of users who have read this message"""
        read_statuses = obj.read_statuses.all()
        return [
            {
                'user_id': status.user.id,
                'username': status.user.username,
                'read_at': status.read_at
            }
            for status in read_statuses
        ]

class ConversationSerializer(serializers.ModelSerializer):
    participants = SimpleUserSerializer(many=True, read_only=True)
    participant_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True
    )
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    other_participant = serializers.SerializerMethodField()
    
    class Meta:
        model = Conversation
        fields = [
            'id', 'participants', 'participant_ids', 'created_at', 
            'updated_at', 'last_message', 'unread_count', 'other_participant'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_last_message(self, obj):
        """Get the last message in the conversation"""
        last_message = obj.messages.filter(is_deleted=False).last()
        if last_message:
            return MessageSerializer(last_message, context=self.context).data
        return None
    
    def get_unread_count(self, obj):
        """Get count of unread messages for the current user"""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return 0
        
        # Count messages not read by current user
        from .models import MessageReadStatus
        read_message_ids = MessageReadStatus.objects.filter(
            user=request.user,
            message__conversation=obj
        ).values_list('message_id', flat=True)
        
        unread_count = obj.messages.exclude(
            id__in=read_message_ids
        ).exclude(
            sender=request.user  # Don't count own messages as unread
        ).filter(
            is_deleted=False
        ).count()
        
        return unread_count
    
    def get_other_participant(self, obj):
        """Get the other participant in a 2-person conversation"""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None
        
        other_participant = obj.get_other_participant(request.user)
        if other_participant:
            return SimpleUserSerializer(other_participant).data
        return None
    
    def create(self, validated_data):
        participant_ids = validated_data.pop('participant_ids')
        conversation = Conversation.objects.create(**validated_data)
        
        # Add participants
        from django.contrib.auth import get_user_model
        User = get_user_model()
        participants = User.objects.filter(id__in=participant_ids)
        conversation.participants.set(participants)
        
        return conversation

class MessageReadStatusSerializer(serializers.ModelSerializer):
    user = SimpleUserSerializer(read_only=True)
    
    class Meta:
        model = MessageReadStatus
        fields = ['id', 'message', 'user', 'read_at']
        read_only_fields = ['id', 'read_at']

from rest_framework import serializers
from .models import User, Comment, Post

class UserIdSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(required=True, min_value=1)

class UserCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'firstname', 'lastname', 'balance', 'is_admin', 'is_banned']
        extra_kwargs = {
            'id': {'required': True},
            'username': {'required': False},
            'balance': {'default': 50},
            'is_admin': {'default': False},
            'is_banned': {'default': False}
        }


class CommentCreateSerializer(serializers.ModelSerializer):
    author_id = serializers.IntegerField(required=True)
    post = serializers.IntegerField(required=True)

    class Meta:
        model = Comment
        fields = ['post', 'author_id', 'content', 'telegram_id']
        extra_kwargs = {
            'content': {'required': True},
            'telegram_id': {'required': False}
        }

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'firstname', 'lastname', 'balance', 'is_admin', 'is_banned']

class PostCreateSerializer(serializers.ModelSerializer):
    author_id = serializers.IntegerField(required=False, allow_null=True)
    
    class Meta:
        model = Post
        fields = ['author_id', 'content', 'posted_at', 'is_posted', 'is_rejected', 'media_type', 'telegram_id']
        extra_kwargs = {
            'content': {'required': True},
            'media_type': {'required': False},
            'telegram_id': {'required': False},
            'posted_at': {'required': True},
            'is_posted': {'required': False},
            'is_rejected': {'required': False}
        }

class PostSerializer(serializers.ModelSerializer):
    class Meta:
        model = Post
        fields = '__all__' 
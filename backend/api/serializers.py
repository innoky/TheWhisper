from rest_framework import serializers
from .models import User, Comment

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
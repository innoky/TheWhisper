from rest_framework import serializers
from .models import User, Comment, Post, PseudoNames, UserPseudoName

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'firstname', 'lastname', 'balance', 'level', 'is_admin', 'is_banned']
        read_only_fields = ['balance', 'level', 'is_banned']

class PostSerializer(serializers.ModelSerializer):
    author = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    class Meta:
        model = Post
        fields = ['id', 'author', 'content', 'media_type', 'posted_at', 'is_rejected', 'is_posted', 'telegram_id', 
                 'channel_message_id', 'channel_posted_at', 'is_paid', 'paid_at']
        read_only_fields = ['is_paid', 'paid_at']

class CommentSerializer(serializers.ModelSerializer):
    author = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    author_details = UserSerializer(source='author', read_only=True)
    
    class Meta:
        model = Comment
        fields = ['id', 'reply_to', 'author', 'author_details', 'content', 'created_at', 'telegram_id']

class PseudoNameSerializer(serializers.ModelSerializer):
    class Meta:
        model = PseudoNames
        fields = ['id', 'pseudo', 'price', 'is_available']

class UserPseudoNameSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    pseudo_name = serializers.PrimaryKeyRelatedField(queryset=PseudoNames.objects.all())
    
    class Meta:
        model = UserPseudoName
        fields = ['id', 'user', 'pseudo_name', 'purchase_date']
        read_only_fields = ['purchase_date']

from rest_framework import serializers
from .models import User, Comment, Post, PseudoNames, UserPseudoName, PromoCode, PromoCodeActivation
from .models import AskPost, AskComment

######################################  USERS BLOCK  ##############################################

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'firstname', 'lastname', 'balance', 'level', 'is_admin', 'is_banned']
        read_only_fields = ['balance', 'level', 'is_banned']


######################################  POSTS BLOCK  ##################################################
"""
==================================
Basic posts serializer
==================================
"""
class AbstractBasePostSerializer(serializers.ModelSerializer):
    author = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    author_details = UserSerializer(source='author', read_only=True)

    class Meta:
        abstract = True
        fields = ['id', 'author', 'author_details', 'content', 'media_type', 'posted_at', 
                  'is_rejected', 'is_posted', 'telegram_id', 'channel_message_id', 
                  'channel_posted_at', 'is_paid', 'paid_at']
        read_only_fields = ['is_paid', 'paid_at']

"""
=====================================
implementation of serializers
=====================================
"""

class AskPostSerializer(AbstractBasePostSerializer):
    class Meta(AbstractBasePostSerializer.Meta):
        model = AskPost


class PostSerializer(AbstractBasePostSerializer):
    class Meta(AbstractBasePostSerializer.Meta):
        model = Post
    
##################################  COMMENTS BLOCK  ####################################################

"""
==================================
Basic comments serializer
==================================
"""
class AbstractBaseCommentSerializer(serializers.ModelSerializer):
    author = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    author_details = UserSerializer(source='author', read_only=True)

    class Meta:
        abstract = True
        fields = ['id', 'reply_to', 'author', 'author_details', 'content', 'created_at', 'telegram_id']

"""
=====================================
implementation of serializers
=====================================
"""

class CommentSerializer(AbstractBaseCommentSerializer):
    class Meta(AbstractBaseCommentSerializer.Meta):
        model = Comment


class AskCommentSerializer(AbstractBaseCommentSerializer):
    class Meta(AbstractBaseCommentSerializer.Meta):
        model = AskComment

###############################################################################################################

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

class PromoCodeSerializer(serializers.ModelSerializer):
    created_by = UserSerializer(read_only=True)
    
    class Meta:
        model = PromoCode
        fields = ['id', 'code', 'description', 'reward_amount', 'max_uses', 'current_uses', 
                 'is_active', 'created_at', 'expires_at', 'created_by']
        read_only_fields = ['created_at', 'created_by']

class PromoCodeActivationSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    promo_code = serializers.PrimaryKeyRelatedField(queryset=PromoCode.objects.all())
    user_details = UserSerializer(source='user', read_only=True)
    promo_code_details = PromoCodeSerializer(source='promo_code', read_only=True)
    
    class Meta:
        model = PromoCodeActivation
        fields = ['id', 'user', 'user_details', 'promo_code', 'promo_code_details', 
                 'activated_at', 'reward_amount']
        read_only_fields = ['activated_at', 'reward_amount']

    def create(self, validated_data):
        """Автоматически устанавливаем reward_amount из промокода"""
        promo_code = validated_data['promo_code']
        validated_data['reward_amount'] = promo_code.reward_amount
        return super().create(validated_data)

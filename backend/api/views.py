from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import User, Comment, Post, PseudoNames, UserPseudoName, PromoCode, PromoCodeActivation
from .serializers import UserSerializer, CommentSerializer, PostSerializer, PseudoNameSerializer, UserPseudoNameSerializer, PromoCodeSerializer, PromoCodeActivationSerializer
from decimal import Decimal
import decimal
from datetime import datetime, timezone
from django.conf import settings

def get_tokens_by_level(level):
    """
    Возвращает количество токенов за пост в зависимости от уровня пользователя.
    Уровни от 1 до 10, токены от 5 до 50.
    """
    if level < 1:
        level = 1
    elif level > 10:
        level = 10
    
    # Формула: базовые 5 токенов + 5 токенов за каждый уровень
    return 50 + (level - 1) * 50

def check_access_token(request):
    token = request.headers.get('X-ACCESS-TOKEN')
    if not token or token != settings.API_ACCESS_TOKEN:
        return False
    return True

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    lookup_field = 'id'
    http_method_names = ['get', 'post', 'put', 'patch', 'delete']

    def create(self, request, *args, **kwargs):
        """Переопределяем метод create для обработки пользователей с указанным id"""
        user_id = request.data.get('id')
        if user_id:
            # Проверяем, существует ли пользователь с таким id
            try:
                user = User.objects.get(id=user_id)
                # Если пользователь существует, обновляем его данные
                serializer = self.get_serializer(user, data=request.data, partial=True)
                serializer.is_valid(raise_exception=True)
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            except User.DoesNotExist:
                # Если пользователь не существует, создаем нового
                pass
        
        # Стандартное создание пользователя
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        """Переопределяем метод update для лучшего логирования"""
        print(f"[UserViewSet] Updating user with data: {request.data}")
        return super().update(request, *args, **kwargs)

    @action(detail=True, methods=['post'])
    def ban(self, request, id=None):
        user = self.get_object()
        user.is_banned = not user.is_banned
        user.save()
        return Response({'id': user.id, 'is_banned': user.is_banned, 'status': 'updated'})

    @action(detail=True, methods=['get'])
    def pseudo_names(self, request, id=None):
        pseudos = UserPseudoName.objects.filter(user_id=id)
        page = self.paginate_queryset(pseudos)
        if page is not None:
            serializer = UserPseudoNameSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = UserPseudoNameSerializer(pseudos, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def addbalance(self, request, id=None):
        if not check_access_token(request):
            return Response({'error': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)
        user = self.get_object()
        amount = request.data.get('amount')
        try:
            amount = Decimal(str(amount))
        except (TypeError, ValueError, decimal.InvalidOperation):
            return Response({'error': 'Invalid amount'}, status=status.HTTP_400_BAD_REQUEST)
        user.balance += amount
        user.save()
        return Response({'id': user.id, 'balance': str(user.balance), 'status': 'balance increased'})

    @action(detail=True, methods=['post'])
    def setbalance(self, request, id=None):
        if not check_access_token(request):
            return Response({'error': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)
        user = self.get_object()
        amount = request.data.get('amount')
        try:
            amount = Decimal(str(amount))
        except (TypeError, ValueError, decimal.InvalidOperation):
            return Response({'error': 'Invalid amount'}, status=status.HTTP_400_BAD_REQUEST)
        user.balance = amount
        user.save()
        return Response({'id': user.id, 'balance': str(user.balance), 'status': 'balance set'})

    @action(detail=True, methods=['post'])
    def setlevel(self, request, id=None):
        """Устанавливает уровень пользователя"""
        user = self.get_object()
        level = request.data.get('level')
        try:
            level = int(level)
            if level < 1 or level > 10:
                return Response({'error': 'Level must be between 1 and 10'}, status=status.HTTP_400_BAD_REQUEST)
        except (TypeError, ValueError):
            return Response({'error': 'Invalid level'}, status=status.HTTP_400_BAD_REQUEST)
        
        user.level = level
        user.save()
        return Response({'id': user.id, 'level': user.level, 'status': 'level set'})

class PostViewSet(viewsets.ModelViewSet):
    queryset = Post.objects.all().order_by('-posted_at')
    serializer_class = PostSerializer
    lookup_field = 'id'

    def get_queryset(self):
        """
        Добавляем фильтрацию по author, telegram_id, is_posted, is_rejected, а также сортировку
        """
        queryset = Post.objects.all()
        author = self.request.query_params.get('author', None)
        telegram_id = self.request.query_params.get('telegram_id', None)
        is_posted = self.request.query_params.get('is_posted', None)
        is_rejected = self.request.query_params.get('is_rejected', None)
        ordering = self.request.query_params.get('ordering', '-posted_at')

        if author is not None:
            queryset = queryset.filter(author=author)
        if telegram_id is not None:
            queryset = queryset.filter(telegram_id=telegram_id)
        if is_posted is not None:
            if is_posted.lower() == 'true':
                queryset = queryset.filter(is_posted=True)
            elif is_posted.lower() == 'false':
                queryset = queryset.filter(is_posted=False)
        if is_rejected is not None:
            if is_rejected.lower() == 'true':
                queryset = queryset.filter(is_rejected=True)
            elif is_rejected.lower() == 'false':
                queryset = queryset.filter(is_rejected=False)
        if ordering:
            queryset = queryset.order_by(ordering)
        return queryset

    def partial_update(self, request, *args, **kwargs):
        """Переопределяем метод partial_update для логирования"""
        print(f"[PostViewSet] Partial update with data: {request.data}")
        return super().partial_update(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        """Переопределяем метод update для логирования"""
        print(f"[PostViewSet] Full update with data: {request.data}")
        return super().update(request, *args, **kwargs)

    @action(detail=True, methods=['post'])
    def mark_as_posted(self, request, id=None):
        post = self.get_object()
        post.is_posted = True
        post.channel_posted_at = datetime.now(timezone.utc)
        post.save()
        return Response({'id': post.id, 'is_posted': post.is_posted, 'channel_posted_at': post.channel_posted_at, 'status': 'updated'})

    @action(detail=True, methods=['post'])
    def mark_as_rejected(self, request, id=None):
        post = self.get_object()
        post.is_rejected = True
        post.save()
        return Response({'id': post.id, 'is_rejected': post.is_rejected, 'status': 'updated'})

    @action(detail=True, methods=['post'])
    def process_payment(self, request, id=None):
        """
        Обрабатывает оплату поста на основе уровня автора.
        Формула: базовые 5 токенов + 5 токенов за каждый уровень
        """
        post = self.get_object()
        
        # Проверяем, что пост еще не оплачен
        if post.is_paid:
            return Response({'error': 'Post already paid'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Проверяем, что пост выложен в канал
        if not post.channel_message_id:
            return Response({'error': 'Post not yet posted to channel'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Проверяем, что у поста есть автор
        if not post.author:
            return Response({'error': 'Post has no author'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Рассчитываем токены на основе уровня автора
        tokens_to_add = get_tokens_by_level(post.author.level)
        
        # Обновляем пост с timezone-aware datetime
        post.is_paid = True
        post.paid_at = datetime.now(timezone.utc)
        post.save()
        
        # Добавляем токены автору поста
        post.author.balance += Decimal(str(tokens_to_add))
        post.author.save()
        
        return Response({
            'id': post.id,
            'author_level': post.author.level,
            'tokens_added': tokens_to_add,
            'author_balance': str(post.author.balance),
            'status': 'payment processed'
        })

    @action(detail=True, methods=['post'])
    def publish_now(self, request, id=None):
        """
        Немедленно публикует пост в канал и обрабатывает оплату.
        """
        post = self.get_object()
        
        # Проверяем, что пост еще не опубликован
        if post.is_posted:
            return Response({'error': 'Post already published'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Проверяем, что у поста есть автор
        if not post.author:
            return Response({'error': 'Post has no author'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Проверяем, что у поста есть telegram_id
        if not post.telegram_id:
            return Response({'error': 'Post has no telegram_id'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Помечаем пост как опубликованный
        post.is_posted = True
        post.channel_posted_at = datetime.now(timezone.utc)
        post.save()
        
        # Обрабатываем оплату сразу
        tokens_to_add = get_tokens_by_level(post.author.level)
        post.is_paid = True
        post.paid_at = datetime.now(timezone.utc)
        post.save()
        
        # Добавляем токены автору поста
        post.author.balance += Decimal(str(tokens_to_add))
        post.author.save()
        
        return Response({
            'id': post.id,
            'telegram_id': post.telegram_id,
            'author_level': post.author.level,
            'tokens_added': tokens_to_add,
            'author_balance': str(post.author.balance),
            'status': 'published and paid'
        })

class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.all().order_by('-created_at')
    serializer_class = CommentSerializer
    lookup_field = 'id'

    def create(self, request, *args, **kwargs):
        """Переопределяем метод create для логирования"""
        print(f"[CommentViewSet] Creating comment with data: {request.data}")
        result = super().create(request, *args, **kwargs)
        print(f"[CommentViewSet] Comment created successfully: {result.data}")
        return result

    def get_queryset(self):
        """
        Добавляем фильтрацию по telegram_id и post (reply_to)
        """
        queryset = Comment.objects.all().order_by('-created_at')
        telegram_id = self.request.query_params.get('telegram_id', None)
        post_id = self.request.query_params.get('post', None)
        if telegram_id is not None:
            queryset = queryset.filter(telegram_id=telegram_id)
        if post_id is not None:
            queryset = queryset.filter(reply_to=post_id)
        return queryset

    @action(detail=False, methods=['get'], url_path='telegram/(?P<telegram_id>[^/.]+)')
    def get_by_telegram_id(self, request, telegram_id=None):
        """
        Получает комментарий по его telegram_id
        """
        print(f"[CommentViewSet] get_by_telegram_id called with telegram_id: {telegram_id}")
        
        try:
            telegram_id = int(telegram_id)
            print(f"[CommentViewSet] Converted telegram_id to int: {telegram_id}")
        except (ValueError, TypeError):
            print(f"[CommentViewSet] Invalid telegram_id format: {telegram_id}")
            return Response({'error': 'Invalid telegram_id format'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            comment = Comment.objects.get(telegram_id=telegram_id)
            print(f"[CommentViewSet] Found comment: {comment.id}, author: {comment.author.id if comment.author else None}")
            serializer = self.get_serializer(comment)
            result = serializer.data
            print(f"[CommentViewSet] Serialized data: {result}")
            return Response(result)
        except Comment.DoesNotExist:
            print(f"[CommentViewSet] Comment with telegram_id {telegram_id} not found")
            return Response({'error': 'Comment not found'}, status=status.HTTP_404_NOT_FOUND)

class PseudoNameViewSet(viewsets.ModelViewSet):
    queryset = PseudoNames.objects.all().order_by('pseudo')
    serializer_class = PseudoNameSerializer
    lookup_field = 'id'

    @action(detail=True, methods=['post'])
    def deactivate(self, request, id=None):
        pseudo = self.get_object()
        pseudo.is_available = False
        pseudo.save()
        return Response({'id': pseudo.id, 'is_available': pseudo.is_available, 'status': 'deactivated'})

class UserPseudoNameViewSet(viewsets.ModelViewSet):
    queryset = UserPseudoName.objects.all()
    serializer_class = UserPseudoNameSerializer
    lookup_field = 'id'

class PromoCodeViewSet(viewsets.ModelViewSet):
    queryset = PromoCode.objects.all()
    serializer_class = PromoCodeSerializer
    lookup_field = 'id'

class PromoCodeActivationViewSet(viewsets.ModelViewSet):
    queryset = PromoCodeActivation.objects.all()
    serializer_class = PromoCodeActivationSerializer
    lookup_field = 'id'
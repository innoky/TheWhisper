from django.shortcuts import render
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import User, Comment, Post
from rest_framework import status
from . import serializers

@api_view(['GET'])
def ping(request):
    """
    A simple view to check if the server is running.
    """
    return Response({"message": "pong"})

@api_view(['GET'])
def get_recent_users(request):
    """
    Возвращает последние 20 добавленных пользователей
    """
    users = User.objects.all().order_by('-id')[:20] 
    serializer = serializers.UserSerializer(users, many=True)
    return Response(serializer.data)

@api_view(['POST'])
def user_exists(request):
    """
    Проверяет существование пользователя по id.
    Принимает JSON: {"user_id": 123}
    Возвращает: {
        "exists": true/false,
        "is_banned": true/false (если пользователь существует)
    }
    """
    serializer = serializers.UserIdSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(
            {"error": "Invalid data", "details": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )

    user_id = serializer.validated_data['user_id']
    
    try:
        user = User.objects.get(id=user_id)
        return Response({
            "exists": True,
            "is_banned": user.is_banned,
            "is_admin": user.is_admin,
            "balance": float(user.balance)  
        }, status=status.HTTP_200_OK)
    except User.DoesNotExist:
        return Response({"exists": False}, status=status.HTTP_200_OK)

@api_view(['POST'])
def create_user(request):
    """
    Создает нового пользователя.
    Принимает JSON с полями пользователя.
    """
    serializer = serializers.UserCreateSerializer(data=request.data)
    
    if serializer.is_valid():
        try:
            user = serializer.save()
            return Response({
                "id": user.id,
                "username": user.username,
                "status": "created"
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    return Response(
        {"errors": serializer.errors},
        status=status.HTTP_400_BAD_REQUEST
    )

@api_view(['POST'])
def create_comment(request):
    """
    Создает комментарий. Все поля обязательные, кроме telegram_id.
    author_id должен существовать в системе (или быть null для анонимных).
    """
    serializer = serializers.CommentCreateSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(
            {"errors": serializer.errors}, 
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
       
        # Обрабатываем автора (может быть null)
        author_id = serializer.validated_data['author_id']
        author = User.objects.get(id=author_id) if author_id else None
        post = serializer.validated_data['post']
        comment = Comment.objects.create(
            post=post,
            author=author,
            content=serializer.validated_data['content'],
            telegram_id=serializer.validated_data.get('telegram_id')
        )

        return Response({
            "id": comment.id,
            "post": post,
            "author_id": author.id if author else None,
            "content": comment.content,
            "created_at": comment.created_at,
            "telegram_id": comment.telegram_id
        }, status=status.HTTP_201_CREATED)

  
    except User.DoesNotExist:
        return Response(
            {"error": "Author not found"},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
def create_post(request):
    """
    Создает новый пост.
    Обязательные поля: content
    Необязательные: author_id, media_type, telegram_id
    """
    serializer = serializers.PostCreateSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(
            {"errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        # Обработка автора (может быть None)
        author_id = serializer.validated_data.get('author_id')
        author = User.objects.get(id=author_id) if author_id else None

        post = Post.objects.create(
            author=author,
            content=serializer.validated_data['content'],
            media_type=serializer.validated_data.get('media_type'),
            telegram_id=serializer.validated_data.get('telegram_id')
        )

        return Response({
            "id": post.id,
            "author_id": post.author.id if post.author else None,
            "content": post.content,
            "created_at": post.created_at,
            "status": "created"
        }, status=status.HTTP_201_CREATED)

    except User.DoesNotExist:
        return Response(
            {"error": "Author not found"},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
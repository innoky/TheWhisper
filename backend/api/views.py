from django.shortcuts import render
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import User, Comment, Post, PseudoNames, UserPseudoName
from rest_framework import status
from django.core.paginator import Paginator
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
        author_id = serializer.validated_data.get('author_id')
        author = User.objects.get(id=author_id) if author_id else None

        post = Post.objects.create(
            author=author,
            content=serializer.validated_data['content'],
            media_type=serializer.validated_data.get('media_type'),
            telegram_id=serializer.validated_data.get('telegram_id'),
            posted_at = serializer.validated_data.get('posted_at'),
            is_rejected = serializer.validated_data.get('is_rejected'),
            is_posted = serializer.validated_data.get('is_posted')
        )

        return Response({
            "id": post.id,
            "author_id": post.author.id if post.author else None,
            "content": post.content,
            "posted_at": post.posted_at,
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

@api_view(['GET'])
def get_last_post(request):
    """
    Возвращает самый последний пост (сортировка по created_at)
    """
    last_post = Post.objects.first()  
    
    if not last_post:
        return Response({"error": "No posts found"}, status=404)
    
    serializer = serializers.PostSerializer(last_post)
    return Response(serializer.data)

@api_view(['GET'])
def get_recent_posts(request):
    """
    Возвращает последние 50 добавленных в очередь постов
    """
    posts = Post.objects.all()[:20] 
    serializer = serializers.PostSerializer(posts, many=True)
    return Response(serializer.data)

@api_view(["POST"])
def mark_post_as_posted(request):
    # Получаем ID поста из тела запроса
    post_id = request.data.get('post_id')
    
    if not post_id:
        return Response(
            {"error": "post_id is required"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        # Ищем пост в базе данных
        post = Post.objects.get(id=post_id)
        
        # Если пост уже помечен как опубликованный
        if post.is_posted:
            return Response(
                {"message": "Post is already marked as posted"},
                status=status.HTTP_200_OK
            )
        
        # Помечаем пост как опубликованный
        post.is_posted = True
        post.save()
        
        return Response(
            {"message": f"Post {post_id} successfully marked as posted"},
            status=status.HTTP_200_OK
        )
            
    except Post.DoesNotExist:
        return Response(
            {"error": f"Post with id {post_id} not found"},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(["POST"])
def mark_post_as_rejected(request):
    # Получаем ID поста из тела запроса
    post_id = request.data.get('post_id')
    
    if not post_id:
        return Response(
            {"error": "post_id is required"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        # Ищем пост в базе данных
        
        post = Post.objects.get(telegram_id=post_id)
        print(post)
        # Если пост уже помечен как опубликованный
        if post.is_rejected:
            return Response(
                {"message": "Post is already marked as rejected"},
                status=status.HTTP_200_OK
            )
        
        # Помечаем пост как опубликованный
        post.is_rejected = True
        post.save()
        
        return Response(
            {"message": f"Post {post_id} successfully marked as rejected"},
            status=status.HTTP_200_OK
        )
            
    except Post.DoesNotExist:
        return Response(
            {"error": f"Post with id {post_id} not found"},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
def assign_pseudo_name(request):
    """
    Assigns a pseudo name to a user.
    Required fields: user_id, pseudo_name_id
    """
    serializer = serializers.UserPseudoNameSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(
            {"errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        user_id = serializer.validated_data['user_id']
        pseudo_name_id = serializer.validated_data['pseudo_name_id']

        # Check if user exists
        user = User.objects.get(id=user_id)
        
        # Check if pseudo name exists
        pseudo_name = PseudoNames.objects.get(id=pseudo_name_id)

        # Create the relationship
        user_pseudo = UserPseudoName.objects.create(
            user=user,
            pseudo_name=pseudo_name
        )

        return Response({
            "id": user_pseudo.id,
            "user_id": user_pseudo.user.id,
            "pseudo_name_id": user_pseudo.pseudo_name.id,
            "purchase_date": user_pseudo.purchase_date,
            "status": "created"
        }, status=status.HTTP_201_CREATED)

    except User.DoesNotExist:
        return Response(
            {"error": "User not found"},
            status=status.HTTP_404_NOT_FOUND
        )
    except PseudoNames.DoesNotExist:
        return Response(
            {"error": "Pseudo name not found"},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
@api_view(['POST'])
def create_pseudo_name(request):
    """
    Creates a new pseudo name.
    Required fields: name
    Optional fields: price, is_available
    """
    serializer = serializers.PseudoNameCreateSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(
            {"errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        pseudo_name = PseudoNames.objects.create(
            name=serializer.validated_data['name'],
            price=serializer.validated_data.get('price', 0),
            is_available=serializer.validated_data.get('is_available', True)
        )

        return Response({
            "id": pseudo_name.id,
            "name": pseudo_name.name,
            "price": str(pseudo_name.price),
            "is_available": pseudo_name.is_available,
            "status": "created"
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
def deactivate_pseudo_name(request):
    """
    Деактивирует псевдоним, устанавливая is_available=False
    Обязательное поле в теле запроса: pseudo_name_id
    """
    serializer = serializers.DeactivatePseudoNameSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(
            {"errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        pseudo_name_id = serializer.validated_data['pseudo_name_id']
        pseudo_name = PseudoNames.objects.get(id=pseudo_name_id)
        
        if not pseudo_name.is_available:
            return Response(
                {
                    "status": "already_deactivated",
                    "message": "Псевдоним уже деактивирован",
                    "pseudo_name_id": pseudo_name.id,
                    "name": pseudo_name.name
                },
                status=status.HTTP_200_OK
            )
        
        pseudo_name.is_available = False
        pseudo_name.save()
        
        return Response({
            "status": "success",
            "message": "Псевдоним успешно деактивирован",
            "pseudo_name_id": pseudo_name.id,
            "name": pseudo_name.name,
            "is_available": pseudo_name.is_available
        }, status=status.HTTP_200_OK)

    except PseudoNames.DoesNotExist:
        return Response(
            {
                "status": "error",
                "error": "Псевдоним не найден",
                "requested_id": pseudo_name_id
            },
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {
                "status": "error",
                "error": str(e)
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
@api_view(['GET'])
def list_pseudo_names(request):
    """
    Возвращает список всех псевдонимов с пагинацией
    Параметры запроса:
    - is_available (bool): фильтр по статусу доступности
    - page (int): номер страницы (по умолчанию 1)
    - page_size (int): элементов на странице (по умолчанию 20)
    """
    try:
        # Получаем параметры фильтрации
        is_available = request.GET.get('is_available')
        if is_available is not None:
            is_available = is_available.lower() == 'true'

        # Фильтрация
        queryset = PseudoNames.objects.all()
        if is_available is not None:
            queryset = queryset.filter(is_available=is_available)

        # Пагинация
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 20))
        paginator = Paginator(queryset.order_by('name'), page_size)
        page_obj = paginator.get_page(page)

        # Сериализация
        serializer = serializers.PseudoNameSerializer(page_obj, many=True)
        
        return Response({
            "status": "success",
            "count": paginator.count,
            "total_pages": paginator.num_pages,
            "current_page": page_obj.number,
            "results": serializer.data
        })

    except Exception as e:
        return Response(
            {
                "status": "error",
                "error": str(e)
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
def get_user_pseudo_names(request, user_id):
    """
    Возвращает все псевдонимы принадлежащие указанному пользователю
    URL параметр: user_id - ID пользователя
    GET параметры:
    - page (int): номер страницы
    - page_size (int): элементов на странице
    """
    try:
        # Проверяем существование пользователя
        user = User.objects.get(id=user_id)
        
        # Получаем все связи пользователь-псевдоним
        user_pseudos = UserPseudoName.objects.filter(user=user).select_related('pseudo_name')
        
        # Пагинация
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 20))
        paginator = Paginator(user_pseudos, page_size)
        page_obj = paginator.get_page(page)
        
        # Сериализация
        serializer = serializers.UserPseudoNameDetailSerializer(page_obj, many=True)
        
        return Response({
            "status": "success",
            "user_id": user_id,
            "count": paginator.count,
            "total_pages": paginator.num_pages,
            "current_page": page_obj.number,
            "results": serializer.data
        })

    except User.DoesNotExist:
        return Response(
            {
                "status": "error",
                "error": "Пользователь не найден",
                "user_id": user_id
            },
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {
                "status": "error",
                "error": str(e)
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
def ban_user(request, user_id):
    """
    Блокировка/разблокировка пользователя
    URL параметр: user_id - ID пользователя
    Возвращает:
    - Новый статус is_banned
    - Сообщение о результате
    """
    try:
        # Получаем пользователя
        user = User.objects.get(id=user_id)
        
        # Меняем статус
        user.is_banned = not user.is_banned
        user.save()
        
        action = "заблокирован" if user.is_banned else "разблокирован"
        
        return Response({
            "status": "success",
            "user_id": user.id,
            "username": user.username,
            "is_banned": user.is_banned,
            "message": f"Пользователь {action}"
        }, status=status.HTTP_200_OK)

    except User.DoesNotExist:
        return Response(
            {
                "status": "error",
                "error": "Пользователь не найден",
                "user_id": user_id
            },
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {
                "status": "error",
                "error": str(e)
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
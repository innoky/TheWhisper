from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import User, Comment, Post, PseudoNames, UserPseudoName
from .serializers import UserSerializer, CommentSerializer, PostSerializer, PseudoNameSerializer, UserPseudoNameSerializer
from decimal import Decimal
import decimal

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    lookup_field = 'id'

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
        user = self.get_object()
        amount = request.data.get('amount')
        try:
            amount = Decimal(str(amount))
        except (TypeError, ValueError, decimal.InvalidOperation):
            return Response({'error': 'Invalid amount'}, status=status.HTTP_400_BAD_REQUEST)
        user.balance = amount
        user.save()
        return Response({'id': user.id, 'balance': str(user.balance), 'status': 'balance set'})

class PostViewSet(viewsets.ModelViewSet):
    queryset = Post.objects.all().order_by('-posted_at')
    serializer_class = PostSerializer
    lookup_field = 'id'

    @action(detail=True, methods=['post'])
    def mark_as_posted(self, request, id=None):
        post = self.get_object()
        post.is_posted = True
        post.save()
        return Response({'id': post.id, 'is_posted': post.is_posted, 'status': 'updated'})

    @action(detail=True, methods=['post'])
    def mark_as_rejected(self, request, id=None):
        post = self.get_object()
        post.is_rejected = True
        post.save()
        return Response({'id': post.id, 'is_rejected': post.is_rejected, 'status': 'updated'})

class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.all().order_by('-created_at')
    serializer_class = CommentSerializer
    lookup_field = 'id'

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
from rest_framework.routers import DefaultRouter
from .views import UserViewSet, PostViewSet, CommentViewSet, PseudoNameViewSet, UserPseudoNameViewSet

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'posts', PostViewSet, basename='post')
router.register(r'comments', CommentViewSet, basename='comment')
router.register(r'pseudo-names', PseudoNameViewSet, basename='pseudoname')
router.register(r'user-pseudo-names', UserPseudoNameViewSet, basename='userpseudoname')

urlpatterns = router.urls


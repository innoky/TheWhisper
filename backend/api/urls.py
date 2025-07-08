from rest_framework.routers import DefaultRouter
from .views import UserViewSet, PostViewSet, CommentViewSet, PseudoNameViewSet, UserPseudoNameViewSet, PromoCodeViewSet, PromoCodeActivationViewSet, AskPostViewSet, AskCommentViewSet

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'posts', PostViewSet, basename='post')
router.register(r'comments', CommentViewSet, basename='comment')
router.register(r'pseudo-names', PseudoNameViewSet, basename='pseudoname')
router.register(r'user-pseudo-names', UserPseudoNameViewSet, basename='userpseudoname')
router.register(r'promo-codes', PromoCodeViewSet, basename='promocode')
router.register(r'promo-code-activations', PromoCodeActivationViewSet, basename='promocodeactivation')
router.register(r'ask-posts', AskPostViewSet, basename='askpost')
router.register(r'ask-comments', AskCommentViewSet, basename='askcomment')

urlpatterns = router.urls


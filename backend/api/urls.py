from django.urls import path
from . import views

urlpatterns = [
    path('ping/', views.ping),
    path('user_exists/', views.user_exists),
    path('create_user/', views.create_user, name='create_user'),
    path('new_comment/', views.create_comment, name='create_anonymous_comment'),
    path('recent_users/', views.get_recent_users, name='recent_users'),
]


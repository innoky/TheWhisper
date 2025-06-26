from django.urls import path
from . import views

urlpatterns = [
    path('ping/', views.ping, name = 'ping_api'),

    
    path('users/exists/', views.user_exists, name = 'existance_user_check'),
    path('users/new/', views.create_user, name='user_create'),
    path('users/recent/', views.get_recent_users, name='recent_users'),

    path('comment/new/', views.create_comment, name='create_anonymous_comment'),

    path('post/new/', views.create_post, name = 'post_create'),
    path('post/get_last/', views.get_last_post, name = 'get_last_post'),
    path('post/get_recent/', views.get_recent_posts, name = 'get_recent_posts'),
    path('post/mark_as_posted/', views.mark_post_as_posted, name = 'mark post as posted'),
    path('post/mark_as_rejected/', views.mark_post_as_rejected, name = 'mark post as rejected')
]


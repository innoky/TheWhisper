from django.urls import path
from . import views

urlpatterns = [
    path('ping/', views.ping, name = 'ping_api'),

    
    path('users/exists/', views.user_exists, name = 'existance_user_check'),
    path('users/new/', views.create_user, name='user_create'),
    path('users/recent/', views.get_recent_users, name='recent_users'),
    path('users/assign_pseudo/',views.assign_pseudo_name, name="assign_pseudo"),
    path('users/<int:user_id>/pseudo-names/', views.get_user_pseudo_names, name='user_pseudo_names'),
    path('users/<int:user_id>/ban/', views.ban_user, name="ban/unban user" ),

    path('pseudo/new/', views.create_pseudo_name, name = 'create new pseudo'),
    path('pseudo/deactivate/', views.deactivate_pseudo_name, name = 'deactivate pseudo name'),
    path('pseudo/get_all/', views.list_pseudo_names, name='get all nicks'),

    path('comment/new/', views.create_comment, name='create_anonymous_comment'),

    path('post/new/', views.create_post, name = 'post_create'),
    path('post/get_last/', views.get_last_post, name = 'get_last_post'),
    path('post/get_recent/', views.get_recent_posts, name = 'get_recent_posts'),
    path('post/mark_as_posted/', views.mark_post_as_posted, name = 'mark post as posted'),
    path('post/mark_as_rejected/', views.mark_post_as_rejected, name = 'mark post as rejected')

    
]


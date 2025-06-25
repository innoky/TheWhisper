
from django.db import models


class User(models.Model):
    id = models.BigIntegerField(primary_key=True)  
    username = models.CharField(max_length=150, null=True, blank=True) 
    firstname = models.CharField(max_length=100, null=True, blank=True)
    lastname = models.CharField(max_length=100, null=True, blank=True)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0) 
   
    is_admin = models.BooleanField(default=False)
    is_banned = models.BooleanField(default=False)

    
    class Meta:
        db_table = "users"
        verbose_name = "User"
        verbose_name_plural = "Users"


class AuthCredential(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    passwd_hash = models.TextField(null=True, blank=True, default=None)
    last_passwd_change = models.DateTimeField(null=True)
    auth_method = models.CharField(max_length=32, default='tg-password')

    class Meta:
        db_table = "auth_credentials"
        verbose_name = "Authentication Credential"
        verbose_name_plural = "Authentication Credentials"


class LoginToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    class Meta:
        db_table = "login_tokens"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['token']),
            models.Index(fields=['expires_at']),
        ]
        verbose_name = "Login Token"
        verbose_name_plural = "Login Tokens"


class Post(models.Model):
   
    id = models.AutoField(primary_key=True)

    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    content = models.TextField()
    media_type = models.CharField(max_length=32, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    is_approved = models.BooleanField(default=False)
    is_rejected = models.BooleanField(default=False)
    
    moderator_comment = models.TextField(blank=True, null=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    
    telegram_id = models.BigIntegerField(null=True, blank=True, unique=True)

    class Meta:
        db_table = "posts"
        ordering = ['-created_at']

class Comment(models.Model):
    id = models.AutoField(primary_key=True)
    post = models.IntegerField()
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    telegram_id = models.BigIntegerField(null=True, blank=True, unique=True)

    class Meta:
        db_table = "comments"
        ordering = ['-created_at']
        verbose_name = "Comment"
        verbose_name_plural = "Comments"

class PseudoNames(models.Model):
    id = models.AutoField(primary_key=True)
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    name = models.CharField(max_length=100, unique=True)
    is_available = models.BooleanField(default=True)

    class Meta:
        db_table = "pseudo_names"
        ordering = ['name']
        verbose_name = "Pseudo Name"
        verbose_name_plural = "Pseudo Names"

class UserPseudoName(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    pseudo_name = models.ForeignKey(PseudoNames, on_delete=models.CASCADE)
    purchase_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "user_pseudo_names"
        unique_together = ('user', 'pseudo_name') 

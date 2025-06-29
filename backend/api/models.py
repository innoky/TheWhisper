from django.db import models


class User(models.Model):
    id = models.BigIntegerField(primary_key=True)  
    username = models.CharField(max_length=150, null=True, blank=True) 
    firstname = models.CharField(max_length=100, null=True, blank=True)
    lastname = models.CharField(max_length=100, null=True, blank=True)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0) 
    level = models.IntegerField(default=1, help_text='Уровень пользователя от 1 до 10')
   
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
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='posts')
    content = models.TextField()
    media_type = models.CharField(max_length=32, null=True, blank=True)
    posted_at = models.DateTimeField()
    
    is_rejected = models.BooleanField(default=False)
    is_posted = models.BooleanField(default=False)

    telegram_id = models.BigIntegerField(null=True, blank=True, unique=True)

    channel_message_id = models.BigIntegerField(null=True, blank=True)  # ID сообщения в канале
    channel_posted_at = models.DateTimeField(null=True, blank=True)     # Когда был выложен в канал
    is_paid = models.BooleanField(default=False)                        # Получена ли оплата
    paid_at = models.DateTimeField(null=True, blank=True)               # Когда была выплачена оплата

    class Meta:
        db_table = "posts"
        ordering = ['-posted_at']

class Comment(models.Model):
    id = models.AutoField(primary_key=True)
    reply_to = models.BigIntegerField(null=True, blank=True, help_text='ID тг-поста или комментария, на который идет ответ')
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='comments')
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
    pseudo = models.CharField(max_length=100, unique=True)
    is_available = models.BooleanField(default=True)

    class Meta:
        db_table = "pseudo_names"
        ordering = ['pseudo']
        verbose_name = "Pseudo Name"
        verbose_name_plural = "Pseudo Names"

class UserPseudoName(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='pseudo_names')
    pseudo_name = models.ForeignKey(PseudoNames, on_delete=models.CASCADE, related_name='user_pseudo_names')
    purchase_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "user_pseudo_names"
        unique_together = ('user', 'pseudo_name') 


class PromoCode(models.Model):
    id = models.AutoField(primary_key=True)
    code = models.CharField(max_length=50, unique=True, help_text='Код промокода (например: nuke_123)')
    description = models.TextField(blank=True, help_text='Описание промокода')
    reward_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text='Сумма награды в токенах')
    max_uses = models.IntegerField(default=1, help_text='Максимальное количество использований (0 = безлимит)')
    current_uses = models.IntegerField(default=0, help_text='Текущее количество использований')
    is_active = models.BooleanField(default=True, help_text='Активен ли промокод')
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True, help_text='Дата истечения промокода (null = бессрочно)')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_promo_codes', help_text='Кто создал промокод')

    class Meta:
        db_table = "promo_codes"
        ordering = ['-created_at']
        verbose_name = "Promo Code"
        verbose_name_plural = "Promo Codes"

    def __str__(self):
        return f"{self.code} ({self.reward_amount} т.)"

    @property
    def is_expired(self):
        """Проверяет, истек ли срок действия промокода"""
        if self.expires_at is None:
            return False
        from django.utils import timezone
        return timezone.now() > self.expires_at

    @property
    def can_be_used(self):
        """Проверяет, можно ли использовать промокод"""
        if not self.is_active:
            return False
        if self.is_expired:
            return False
        if self.max_uses > 0 and self.current_uses >= self.max_uses:
            return False
        return True


class PromoCodeActivation(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='promo_code_activations')
    promo_code = models.ForeignKey(PromoCode, on_delete=models.CASCADE, related_name='activations')
    activated_at = models.DateTimeField(auto_now_add=True)
    reward_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text='Сумма награды, полученная при активации')

    class Meta:
        db_table = "promo_code_activations"
        ordering = ['-activated_at']
        unique_together = ('user', 'promo_code')  # Пользователь может активировать промокод только один раз
        verbose_name = "Promo Code Activation"
        verbose_name_plural = "Promo Code Activations"

    def __str__(self):
        return f"{self.user.id} activated {self.promo_code.code}"

    def save(self, *args, **kwargs):
        """При сохранении увеличиваем счетчик использований промокода и устанавливаем reward_amount"""
        if not self.pk:  # Только при создании новой записи
            # Устанавливаем reward_amount из промокода, если не задан
            if not self.reward_amount:
                self.reward_amount = self.promo_code.reward_amount
            self.promo_code.current_uses += 1
            self.promo_code.save()
        super().save(*args, **kwargs) 
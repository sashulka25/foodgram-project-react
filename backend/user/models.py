from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models

from user.constants import MAX_FIELD_LENGTH, MAX_LENGTH_EMAIL


class User(AbstractUser):
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    email = models.EmailField(
        max_length=MAX_LENGTH_EMAIL,
        unique=True,
        blank=False,
        verbose_name='Email'
    )
    username = models.CharField(
        max_length=MAX_FIELD_LENGTH,
        unique=True,
        blank=False,
        validators=[
            RegexValidator(r'^[\w.@+-]+\Z'),
        ],
        verbose_name='Логин'
    )
    first_name = models.CharField(
        max_length=MAX_FIELD_LENGTH,
        unique=True,
        blank=False,
        verbose_name='Имя'
    )
    last_name = models.CharField(
        max_length=MAX_FIELD_LENGTH,
        unique=True,
        blank=False,
        verbose_name='Фамилия'
    )
    password = models.CharField(
        max_length=MAX_FIELD_LENGTH,
        blank=False,
        validators=[
            RegexValidator(r'^[\w.@+-]+\Z'),
        ],
        verbose_name='Пароль'
    )

    class Meta:
        ordering = ('username',)
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self) -> str:
        return self.username


class Subscription(models.Model):
    user = models.ForeignKey(
        User,
        related_name='subscriber',
        verbose_name='Подписчик',
        on_delete=models.CASCADE
    )
    author = models.ForeignKey(
        User,
        related_name='author',
        verbose_name='Автор',
        on_delete=models.CASCADE
    )

    class Meta:
        ordering = ('author',)
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'author'],
                name='unique_user_author'
            ),
            models.CheckConstraint(
                check=~models.Q(user=models.F('author')),
                name='users_cannot_rate_themselves'
            )
        ]

    def __str__(self):
        return (f'Пользователь {self.user} '
                f'добавил автора {self.author} в Подписки.')

from django.core.validators import (MinValueValidator, MaxValueValidator,
                                    RegexValidator)
from django.db import models

from recipes.constants import (MAX_FIELD_LENGTH, MAX_FIELD_LENGTH_RECIPE,
                               MAX_LENGTH_COLOR, MAX_TIME, MAX_VALUE,
                               MIN_VALUE)
from user.models import User


class Ingredient(models.Model):
    name = models.CharField(
        verbose_name='Наименование ингредиента',
        max_length=MAX_FIELD_LENGTH
    )
    measurement_unit = models.CharField(
        verbose_name='Единица измерения',
        max_length=MAX_FIELD_LENGTH
    )

    class Meta:
        ordering = ('name',)
        verbose_name = 'Ингредиент'
        verbose_name_plural = 'Ингредиенты'
        constraints = [
            models.UniqueConstraint(
                fields=['name', 'measurement_unit'],
                name='unique_ingredient_unit'
            )
        ]

    def __str__(self):
        return self.name


class Tag(models.Model):
    name = models.CharField(
        verbose_name='Наименование тега',
        max_length=MAX_FIELD_LENGTH,
        unique=True
    )
    color = models.CharField(
        verbose_name='Цветовой HEX-код',
        unique=True,
        max_length=MAX_LENGTH_COLOR,
        validators=[
            RegexValidator(
                regex='^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$',
                message='Введенное значение не является цветом в формате HEX!'
            )
        ]
    )
    slug = models.SlugField(
        verbose_name='Slug',
        max_length=MAX_FIELD_LENGTH,
        unique=True,
        validators=[
            RegexValidator(r'^[-a-zA-Z0-9_]+$'),
        ],
    )

    class Meta:
        verbose_name = 'Тег'
        verbose_name_plural = 'Теги'

    def __str__(self):
        return self.name


class Recipe(models.Model):
    tags = models.ManyToManyField(
        Tag,
        related_name='recipes',
        verbose_name='Теги'
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='recipes',
        verbose_name='Автор рецепта'
    )
    ingredients = models.ManyToManyField(
        Ingredient,
        related_name='recipes',
        verbose_name='Ингредиенты'
    )
    name = models.TextField(
        verbose_name='Наименование рецепта',
        max_length=MAX_FIELD_LENGTH
    )
    image = models.ImageField(
        upload_to='recipes/',
        null=True,
        default=None,
        verbose_name='Изображение'
    )
    text = models.TextField(
        null=True,
        default=None,
        verbose_name='Описание рецепта',
        max_length=MAX_FIELD_LENGTH_RECIPE
    )
    cooking_time = models.PositiveIntegerField(
        validators=[
            MinValueValidator(MIN_VALUE),
            MaxValueValidator(MAX_TIME)],
        verbose_name='Вермя приготовления в минутах'
    )
    pub_date = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата публикации'
    )

    class Meta:
        ordering = ('-pub_date',)
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'

    def __str__(self):
        return self.name


class IngredientRecipe(models.Model):
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        verbose_name='Рецепт'
    )
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        verbose_name='Ингредиент'
    )
    amount = models.PositiveIntegerField(
        validators=[
            MinValueValidator(MIN_VALUE),
            MaxValueValidator(MAX_VALUE)],
        verbose_name='Количество'
    )

    class Meta:
        verbose_name = 'Ингредиент рецепта'
        verbose_name_plural = 'Ингредиенты рецепта'
        constraints = (
            models.UniqueConstraint(
                fields=('recipe', 'ingredient'),
                name='unique_recipe_ingredient'
            ),
        )

    def __str__(self):
        return f'Рецепт {self.recipe} содержит ингредиент {self.ingredient}'


class TagRecipe(models.Model):
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        verbose_name='Рецепт'
    )
    tag = models.ForeignKey(
        Tag,
        on_delete=models.CASCADE,
        verbose_name='Тег'
    )

    class Meta:
        verbose_name = 'Тег рецепта'
        verbose_name_plural = 'Теги рецепта'
        constraints = (
            models.UniqueConstraint(
                fields=('recipe', 'tag'),
                name='unique_recipe_tag'
            ),
        )

    def __str__(self):
        return f'Рецепт {self.recipe} содержит тег {self.tag}'


class CommonFields(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='%(class)ss',
        verbose_name='Пользователь',
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='%(class)ss',
        verbose_name='Рецепт',
    )
    added_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата и время добавления'
    )

    class Meta:
        abstract = True
        ordering = ('-added_at', )
        constraints = (
            models.UniqueConstraint(
                fields=('user', 'recipe'),
                name='unique_user_recipe'
            ),
        )

    def __str__(self):
        return (f'Пользователь {self.user} '
                f'добавил рецепт {self.recipe} в {self._meta.verbose_name}.')


class Favorite(CommonFields):

    class Meta:
        verbose_name = 'Избранное'
        verbose_name_plural = 'Избранное'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'recipe'],
                name='unique_favourite')
        ]

    def __str__(self):
        return f'{self.user} добавил "{self.recipe}" в Избранное'


class ShoppingCart(CommonFields):

    class Meta:
        verbose_name = 'Список покупок'
        verbose_name_plural = 'Список покупок'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'recipe'],
                name='unique_shopping_cart')
        ]

    def __str__(self):
        return f'{self.user} добавил "{self.recipe}" в Список покупок'

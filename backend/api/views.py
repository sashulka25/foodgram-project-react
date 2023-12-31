from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from djoser.views import UserViewSet
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.viewsets import (ModelViewSet, ReadOnlyModelViewSet)
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from api.filters import IngredientFilter, RecipeFilter
from api.serializers import (CustomUserCreateSerializer, CustomUserSerializer,
                             IngredientSerializer, RecipeCreateSerializer,
                             RecipeSerializer, SubscriptionSerializer,
                             TagSerializer)
from api.pagination import CustomPagination
from api.permissions import IsAuthorOrAdminOrReadOnly
from recipes.models import (Ingredient, IngredientRecipe, Favorite, Recipe,
                            ShoppingCart, Tag)
from user.models import Subscription, User


class IngredientViewSet(ReadOnlyModelViewSet):
    serializer_class = IngredientSerializer
    queryset = Ingredient.objects.all()
    permission_classes = (IsAuthorOrAdminOrReadOnly,)
    pagination_class = None
    filter_backends = (DjangoFilterBackend,)
    filterset_class = IngredientFilter


class TagViewSet(ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    pagination_class = None
    serializer_class = TagSerializer
    permission_classes = (IsAuthorOrAdminOrReadOnly,)


class RecipeViewSet(ModelViewSet):
    queryset = Recipe.objects.all()
    permission_classes = (IsAuthorOrAdminOrReadOnly,)
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter
    pagination_class = CustomPagination

    def get_serializer_class(self):
        if self.action in ('create', 'partial_update'):
            return RecipeCreateSerializer
        return RecipeSerializer

    def perform_create(self, serializer):
        serializer.save()

    def post_delete(self, request, pk, model):
        recipe = self.get_object()
        model_filter = model.objects.filter(
            user=request.user, recipe=recipe)

        if request.method == 'POST':
            if model_filter.exists():
                return Response(
                    {'message': 'Рецепт уже был добавлен'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            model.objects.create(user=request.user, recipe=recipe)
            return Response(
                {'message': 'Рецепт добавлен'},
                status=status.HTTP_200_OK
            )

        if model_filter.exists():
            model_filter.delete()
            return Response(
                {'message': 'Рецепт удален'},
                status=status.HTTP_200_OK
            )
        return Response(
            {'message': 'Данный рецепт отсутствует'},
            status=status.HTTP_400_BAD_REQUEST
        )

    @action(detail=True,
            methods=['post', 'delete'],
            permission_classes=[IsAuthenticated])
    def favorite(self, request, pk=None):
        return self.post_delete(request, pk, Favorite)

    @action(detail=True,
            methods=['post', 'delete'],
            permission_classes=[IsAuthenticated])
    def shopping_cart(self, request, pk=None):
        return self.post_delete(request, pk, ShoppingCart)

    @action(detail=False,
            methods=['get'],
            permission_classes=[IsAuthenticated])
    def download_shopping_cart(self, request):
        recipes = ShoppingCart.objects.filter(
            user=request.user).values('recipe__id')
        ingredients = IngredientRecipe.objects.filter(
            recipe__in=recipes).values(
                'ingredient__name',
                'ingredient__measurement_unit').annotate(
                    quantity=Sum('amount'))
        today = timezone.localdate()
        content = ('Список покупок:\n\n'
                   f'Дата: {today:%Y-%m-%d}\n\n')
        for ingredient in ingredients:
            content += '\n'.join([
                f'- {ingredient["ingredient__name"]} '
                f'({ingredient["ingredient__measurement_unit"]})'
                f' : {ingredient["quantity"]}\n'
            ])
        response = HttpResponse(content, content_type='text/plain')
        response['Content-Disposition'] = ('attachment; '
                                           'filename="shopping_cart.txt"')
        return response


class CustomUserViewSet(UserViewSet):
    queryset = User.objects.all()
    pagination_class = CustomPagination
    serializer_class = CustomUserSerializer
    permission_classes = (AllowAny,)

    def get_serializer_class(self):
        if self.action == 'create':
            return CustomUserCreateSerializer
        elif self.action == 'subscriptions':
            return SubscriptionSerializer
        return CustomUserSerializer

    @action(detail=False,
            methods=['get'],
            serializer_class=SubscriptionSerializer,
            permission_classes=[IsAuthenticated])
    def subscriptions(self, request):
        user_subscriptions = Subscription.objects.filter(user=request.user)
        author_ids = user_subscriptions.values_list('author_id', flat=True)
        queryset = User.objects.filter(pk__in=author_ids)
        paginated_queryset = self.paginate_queryset(queryset)
        serializer = self.get_serializer(paginated_queryset, many=True)
        return self.get_paginated_response(serializer.data)

    @action(detail=False,
            methods=['get'],
            url_path='me',
            url_name='me')
    def my_profile(self, request):
        if not request.user.is_authenticated:
            return Response(
                {'detail': 'Пользователь не авторизован'}, status=401)
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(
        detail=True,
        methods=['post', 'delete'],
        permission_classes=[IsAuthenticated]
    )
    def subscribe(self, request, id):
        user = request.user
        author = get_object_or_404(User, id=id)

        if user == author:
            return Response({'message': 'Подписка на себя невозможна'},
                            status=status.HTTP_400_BAD_REQUEST)

        subscription_exists = Subscription.objects.filter(
            user=user, author=author).exists()

        if request.method == 'POST':
            if subscription_exists:
                return Response({'message': 'Вы уже подписаны '
                                 'на данного автора'},
                                status=status.HTTP_400_BAD_REQUEST)

            Subscription.objects.create(user=user, author=author)
            serializer = SubscriptionSerializer(
                author, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if not subscription_exists:
            return Response(
                {'message': 'Вы не подписаны на данного автора'},
                status=status.HTTP_400_BAD_REQUEST)

        Subscription.objects.filter(
            user=user, author=author).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['post'])
    def set_password(self, request):
        current_password = request.data.get('current_password')
        new_password = request.data.get('new_password')

        if not request.user.is_authenticated:
            raise PermissionDenied(
                detail='Пользователь не авторизован',
                code=status.HTTP_401_UNAUTHORIZED)

        if not request.user.check_password(current_password):
            raise ValidationError(
                {'current_password': ['Неверный пароль']})

        request.user.set_password(new_password)
        request.user.save()

        return Response({'detail': 'Пароль успешно изменен'},
                        status=status.HTTP_204_NO_CONTENT)

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.viewsets import (GenericViewSet, ModelViewSet,
                                     ReadOnlyModelViewSet)
from rest_framework.permissions import IsAuthenticated
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

    @action(detail=True,
            methods=['post', 'delete'],
            permission_classes=[IsAuthorOrAdminOrReadOnly,])
    def favorite(self, request, pk=None):
        recipe = self.get_object()

        if request.method == 'POST':
            if not Favorite.objects.filter(
                    user=request.user, recipe=recipe).exists():
                Favorite.objects.create(user=request.user, recipe=recipe)
                return Response({'message': 'Рецепт добавлен в избранное'},
                                status=status.HTTP_200_OK)
            return Response({'message': 'Рецепт уже в избранном'},
                            status=status.HTTP_400_BAD_REQUEST)

        if request.method == 'DELETE':
            if Favorite.objects.filter(
                    user=request.user, recipe=recipe).exists():
                Favorite.objects.filter(
                    user=request.user, recipe=recipe).delete()
                return Response({'message': 'Рецепт удален из избранного'},
                                status=status.HTTP_200_OK)
            return Response({'message': 'Рецепта нет в избранном'},
                            status=status.HTTP_400_BAD_REQUEST)

        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    @action(detail=True,
            methods=['post', 'delete'],
            permission_classes=[IsAuthenticated])
    def shopping_cart(self, request, pk=None):
        recipe = self.get_object()

        if request.method == 'POST':
            if ShoppingCart.objects.filter(
                    user=request.user, recipe=recipe).exists():
                return Response(
                    {'message': 'Рецепт уже добавлен в список покупок'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            ShoppingCart.objects.create(user=request.user, recipe=recipe)
            return Response(
                {'message': 'Рецепт добавлен в список покупок'},
                status=status.HTTP_200_OK
            )

        if request.method == 'DELETE':
            if ShoppingCart.objects.filter(
                    user=request.user, recipe=recipe).exists():
                ShoppingCart.objects.filter(
                    user=request.user, recipe=recipe).delete()
                return Response(
                    {'message': 'Рецепт удален из списка покупок'},
                    status=status.HTTP_200_OK
                )
            return Response(
                {'message': 'Рецепта нет в списке покупок'},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    @action(detail=False,
            methods=['get'],
            permission_classes=[IsAuthenticated])
    def download_shopping_cart(self, request):
        shopping_cart_items = ShoppingCart.objects.filter(user=request.user)
        buy_list = {}
        for item in shopping_cart_items:
            ingredients = IngredientRecipe.objects.filter(recipe=item.recipe)
            for ingredient in ingredients:
                key = (
                    f'{ingredient.ingredient.name} '
                    f'({ingredient.ingredient.measurement_unit})'
                )
                if key in buy_list:
                    buy_list[key] += ingredient.amount
                else:
                    buy_list[key] = ingredient.amount

        today = timezone.localdate()
        content = ('Список покупок:\n\n'
                   f'Дата: {today:%Y-%m-%d}\n\n')
        for ingredient, amount in buy_list.items():
            content += f'- {ingredient}: {amount}\n'

        response = HttpResponse(content, content_type='text/plain')
        response['Content-Disposition'] = ('attachment; '
                                           'filename="shopping_cart.txt"')

        return response

    def get_queryset(self):
        queryset = super().get_queryset()
        author_id = self.request.query_params.get('author')
        if author_id:
            queryset = queryset.filter(author_id=author_id)
        return queryset


class CustomUserViewSet(GenericViewSet):
    queryset = User.objects.all()
    pagination_class = CustomPagination

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

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        if not request.user.is_authenticated:
            raise PermissionDenied(
                detail='Пользователь не авторизован',
                code=status.HTTP_401_UNAUTHORIZED)
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @action(detail=False,
            methods=['get'],
            url_path='me',
            url_name='me')
    def my_profile(self, request):
        if request.user.is_authenticated:
            serializer = self.get_serializer(request.user)
            return Response(serializer.data)

        return Response({'detail': 'Пользователь не авторизован'}, status=401)

    @action(
        detail=True,
        methods=['post', 'delete'],
        serializer_class=SubscriptionSerializer,
        permission_classes=[IsAuthenticated]
    )
    def subscribe(self, request, pk):
        user = request.user
        author = get_object_or_404(User, pk=pk)

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

        elif request.method == 'DELETE':
            if not subscription_exists:
                return Response(
                    {'message': 'Вы не подписаны на данного автора'},
                    status=status.HTTP_400_BAD_REQUEST)

            Subscription.objects.filter(
                user=user, author=author).delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        return Response({'message': 'Метод не разрешен для данного запроса'},
                        status=status.HTTP_405_METHOD_NOT_ALLOWED)

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

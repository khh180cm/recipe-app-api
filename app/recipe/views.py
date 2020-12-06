from rest_framework import viewsets, mixins
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated

from core.models import Tag, Ingredient, Recipe
from recipe import serializers


class BaseRecipeAttrViewSet(viewsets.GenericViewSet,
                            mixins.ListModelMixin,
                            mixins.CreateModelMixin):
    '''Base viewset for user owned recipe attributes'''
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        '''Return objects for the current authenticated user only'''
        return self.queryset.filter(
                user=self.request.user).order_by('-name')

    def perform_create(self, serializer):
        '''Create a new object'''
        serializer.save(user=self.request.user)


class TagViewSet(BaseRecipeAttrViewSet):
    '''Manage tags in the database'''
    queryset = Tag.objects.all()
    serializer_class = serializers.TagSerializer


class IngredientViewSet(BaseRecipeAttrViewSet):
    '''Manage ingredients in the database'''
    queryset = Ingredient.objects.all()
    serializer_class = serializers.IngredientSerializer


class RecipeViewSet(viewsets.ModelViewSet):
    '''Manage recipes in the database'''
    queryset = Recipe.objects.all()
    serializer_class = serializers.RecipeSerializer
    authentication_classess = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)

    def _params_to_ints(self, qs):
        '''Convert a list of string IDs to a list of integers'''
        return [int(str_id) for str_id in qs.split(',')]

    def get_queryset(self):
        '''Retrieve objects for the current authenticated user only'''
        tags = self.request.query_params.get('tag')
        ingredients = self.request.query_params.get('ingredient')
        queryset = self.queryset
        if tags:
            tag_ids = self._params_to_ints(tags)
            queryset = queryset.filter(tag__id__in=tag_ids)
        if ingredients:
            ingredient_ids = self._params_to_ints(ingredients)
            queryset = queryset.filter(ingredient__id__in=ingredient_ids)

        return queryset.filter(user=self.request.user)

    def get_serializer_class(self):
        '''Return appropriate serializer class'''
        if self.action == 'retrieve':
            return serializers.RecipeDetailSerializer
        return self.serializer_class

    def perform_create(self, serializer):
        '''Create a new recipe'''
        serializer.save(user=self.request.user)

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

from core.models import Recipe, Tag, Ingredient
from recipe.serializers import RecipeSerializer, RecipeDetailSerializer


RECIPES_URL = reverse('recipe:recipe-list')


def detail_url(recipe_id):
    '''
    Return recipe detail URL
    (example) /api/recipe/recipes/1
    '''
    return reverse('recipe:recipe-detail', args=[recipe_id])


def sample_tag(user, name='Main course'):
    '''Create and return a sample tag'''
    return Tag.objects.create(user=user, name=name)


def sample_ingredient(user, name='Cinnamon'):
    '''Create and return a sample ingredient'''
    return Ingredient.objects.create(user=user, name=name)


def sample_recipe(user, **params):
    '''
    Create and return a sample recipe [Helper funcion]
    '''
    defaults = {
        'title': 'Sample recipe',
        'time_minute': 10,
        'price': 100.35
    }
    # override the defaults by **params
    defaults.update(params)

    return Recipe.objects.create(user=user, **defaults)


class PublicRecipeApiTest(TestCase):
    '''Test unauthenticated recipe API access'''

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        '''Test the authentication is required'''
        res = self.client.get(RECIPES_URL)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class PrivateRecipeApiTest(TestCase):
    '''Test authenticated recipe API access'''

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            'test@test.co.kr',
            '1234431'
        )
        self.client.force_authenticate(self.user)

    def test_retrieve_recipe(self):
        '''Test retrieving a list of recipes'''
        sample_recipe(user=self.user)
        sample_recipe(user=self.user)

        res = self.client.get(RECIPES_URL)
        recipes = Recipe.objects.all().order_by('-id')
        serializer = RecipeSerializer(recipes, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_recipes_limited_to_user(self):
        '''Test retrieving recipes for user'''
        user2 = get_user_model().objects.create_user(
            'user2@user.co.kr',
            '1q2w3e4r'
        )
        sample_recipe(user=user2)
        sample_recipe(user=self.user)

        res = self.client.get(RECIPES_URL)

        recipes = Recipe.objects.filter(user=self.user)
        serializer = RecipeSerializer(recipes, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data, serializer.data)

    def test_view_recipe_detail(self):
        '''Test viewing a recipe detail'''
        recipe = sample_recipe(user=self.user)
        recipe.tag.add(sample_tag(user=self.user))
        recipe.ingredient.add(sample_ingredient(user=self.user))

        url = detail_url(recipe.id)

        res = self.client.get(url)
        serializer = RecipeDetailSerializer(recipe)

        self.assertEqual(res.data, serializer.data)

    def test_create_basic_recipe(self):
        '''
        Test creating recipe'''
        payload = {
            'title': 'chocolate',
            'time_minute': 30,
            'price': 5.00
        }

        res = self.client.post(RECIPES_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipe = Recipe.objects.get(id=res.data['id'])

        for key in payload.keys():
            self.assertEqual(payload[key], getattr(recipe, key))

    def test_create_recipe_with_tags(self):
        '''Test creating a recipe with tags'''
        tag1 = sample_tag(user=self.user, name='Vegan')
        tag2 = sample_tag(user=self.user, name='Dessert')

        payload = {
            'title': 'Avocado lime cheezecake',
            'tag': [tag1.id, tag2.id],
            'time_minute': 60,
            'price': 20.00
        }

        res = self.client.post(RECIPES_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipe = Recipe.objects.get(id=res.data['id'])
        tags = recipe.tag.all()

        self.assertEqual(tags.count(), 2)
        self.assertIn(tag1, tags)
        self.assertIn(tag2, tags)

    def test_create_recipe_with_ingredients(self):
        '''Test creating recipe with ingredients'''
        ingredient1 = sample_ingredient(user=self.user, name='Banana')
        ingredient2 = sample_ingredient(user=self.user, name='Apple')

        payload = {
            'title': 'Thai prawn red curry',
            'ingredient': [ingredient1.id, ingredient2.id],
            'time_minute': 20,
            'price': 7.00
        }

        res = self.client.post(RECIPES_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipe = Recipe.objects.get(id=res.data['id'])
        ingredients = recipe.ingredient.all()

        self.assertEqual(ingredients.count(), 2)
        self.assertIn(ingredient1, ingredients)
        self.assertIn(ingredient2, ingredients)

    def test_partial_update_recipe(self):
        '''Test updating a recipe with patch'''
        recipe = sample_recipe(user=self.user)
        recipe.tag.add(sample_tag(user=self.user))
        new_tag = sample_tag(user=self.user, name='Curry')

        payload = {'title': 'Chicken tikka', 'tag': [new_tag.id]}
        url = detail_url(recipe.id)
        self.client.patch(url, payload)

        recipe.refresh_from_db()
        self.assertEqual(recipe.title, payload['title'])
        tags = recipe.tag.all()
        self.assertEqual(len(tags), 1)
        self.assertIn(new_tag, tags)

    def test_full_update_recipe(self):
        '''Test updating a recipe with put method'''
        recipe = sample_recipe(user=self.user)
        recipe.tag.add(sample_tag(user=self.user))
        payload = {
            'title': 'Spaghetti carbonara',
            'time_minute': 25,
            'price': 5.00
        }
        url = detail_url(recipe.id)
        self.client.put(url, payload)

        recipe.refresh_from_db()
        self.assertEqual(recipe.title, payload['title'])
        self.assertEqual(recipe.time_minute, payload['time_minute'])
        self.assertEqual(recipe.price, payload['price'])
        tags = recipe.tag.all()
        self.assertEqual(len(tags), 0)

    def test_filter_recipes_by_tags(self):
        '''Test returning recipes with specific tags'''
        recipe_1 = sample_recipe(user=self.user, title='Thai vegetable curry')
        recipe_2 = sample_recipe(user=self.user, title='Aubergine with tahini')
        tag_1 = sample_tag(user=self.user, name='Vegan')
        tag_2 = sample_tag(user=self.user, name='Vegetarian')
        recipe_1.tag.add(tag_1)
        recipe_2.tag.add(tag_2)
        recipe_3 = sample_recipe(user=self.user, title='Fish and chips')

        res = self.client.get(
            RECIPES_URL,
            {'tag': f'{tag_1.id}, {tag_2.id}'}
        )

        serializer_1 = RecipeSerializer(recipe_1)
        serializer_2 = RecipeSerializer(recipe_2)
        serializer_3 = RecipeSerializer(recipe_3)

        self.assertIn(serializer_1.data, res.data)
        self.assertIn(serializer_2.data, res.data)
        self.assertNotIn(serializer_3.data, res.data)

    def test_filter_recipes_by_ingredients(self):
        '''Test returning recipes with specific ingredients'''
        recipe_1 = sample_recipe(user=self.user, title='Posh beans on toast')
        recipe_2 = sample_recipe(user=self.user, title='Chicken cacciatore')
        ingredient_1 = sample_ingredient(user=self.user, name='Feta cheeze')
        ingredient_2 = sample_ingredient(user=self.user, name='Chicken')
        recipe_1.ingredient.add(ingredient_1)
        recipe_2.ingredient.add(ingredient_2)
        recipe_3 = sample_recipe(user=self.user, title='Steak and mushrooms')

        res = self.client.get(
            RECIPES_URL,
            {'ingredient': f'{ingredient_1.id}, {ingredient_2.id}'}
        )

        serializer_1 = RecipeSerializer(recipe_1)
        serializer_2 = RecipeSerializer(recipe_2)
        serializer_3 = RecipeSerializer(recipe_3)

        self.assertIn(serializer_1.data, res.data)
        self.assertIn(serializer_2.data, res.data)
        self.assertNotIn(serializer_3.data, res.data)

# app/recipe/tests/test_recipe_api.py
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from core.models import Recipe, Tag
from recipe.serializers import RecipeSerializer, RecipeDetailSerializer

RECIPE_URL = reverse('recipe:recipe-list')  # 食谱列表的URL


def detail_url(recipe_id):
    return reverse('recipe:recipe-detail', args=[recipe_id])  # 生成食谱详情的URL


def create_recipe(user, **params):
    defaults = {
        'title': 'Sample Recipe',
        'time_minutes': 22,
        'price': Decimal('5.25'),
        'description': 'Sample Description',
        'link': 'http://sample.com/recipe.pdf'
    }

    defaults.update(params)

    recipe = Recipe.objects.create(user=user, **defaults)  # 创建食谱
    return recipe


def create_user(**params):
    return get_user_model().objects.create_user(**params)  # 创建用户


class PublicRecipeApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()  # 初始化API客户端

    def test_auth_required(self):
        res = self.client.get(RECIPE_URL)  # 未认证用户访问食谱列表

        # 断言返回401未认证
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateRecipeApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()  # 初始化API客户端
        self.user = create_user(
            email='user@example.com',
            password='testpass'
        )  # 创建并认证用户
        self.client.force_authenticate(self.user)

    def test_retrieve_recipes(self):
        create_recipe(user=self.user)  # 创建食谱
        create_recipe(user=self.user)

        res = self.client.get(RECIPE_URL)  # 获取食谱列表

        recipes = Recipe.objects.all().order_by('-id')  # 查询所有食谱并按id降序排列
        serializer = RecipeSerializer(recipes, many=True)  # 序列化食谱列表

        self.assertEqual(res.status_code, status.HTTP_200_OK)  # 断言返回200成功
        self.assertEqual(res.data, serializer.data)  # 断言返回数据与序列化数据一致

    def test_recipe_list_limited_to_user(self):
        other_user = create_user(
            email='other@example.com',
            password='testpass'
        )  # 创建其他用户

        create_recipe(user=other_user)  # 创建其他用户的食谱
        create_recipe(user=self.user)  # 创建当前用户的食谱

        res = self.client.get(RECIPE_URL)  # 获取食谱列表

        recipes = Recipe.objects.filter(user=self.user)  # 查询当前用户的食谱
        serializer = RecipeSerializer(recipes, many=True)  # 序列化食谱列表

        self.assertEqual(res.status_code, status.HTTP_200_OK)  # 断言返回200成功
        self.assertEqual(res.data, serializer.data)  # 断言返回数据与序列化数据一致

    def test_get_recipe_detail(self):
        recipe = create_recipe(user=self.user)  # 创建食谱
        url = detail_url(recipe.id)  # 获取食谱详情的URL
        res = self.client.get(url)  # 获取食谱详情

        serializer = RecipeDetailSerializer(recipe)  # 序列化食谱详情

        self.assertEqual(res.data, serializer.data)  # 断言返回数据与序列化数据一致

    def test_create_recipe(self):
        payload = {
            'title': 'Chocolate cheesecake',
            'time_minutes': 30,
            'price': Decimal('5.99'),
        }

        res = self.client.post(RECIPE_URL, payload)  # 创建食谱
        # 断言返回201创建成功
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipe = Recipe.objects.get(id=res.data['id'])  # 获取创建的食谱
        for k, v in payload.items():
            self.assertEqual(v, getattr(recipe, k))  # 断言返回数据与输入数据一致
        self.assertEqual(recipe.user, self.user)  # 断言食谱用户为当前用户

    def test_partial_update(self):
        original_link = 'http://sample.com/recipe.pdf'
        recipe = create_recipe(
            user=self.user,
            title='Sample recipe title',
            link=original_link
        )

        payload = {
            'title': 'New recipe title',
        }

        url = detail_url(recipe.id)  # 获取食谱详情的URL
        res = self.client.patch(url, payload)  # 部分更新食谱

        self.assertEqual(res.status_code, status.HTTP_200_OK)  # 断言返回200成功
        recipe.refresh_from_db()
        self.assertEqual(recipe.title, payload['title'])  # 断言标题更新成功
        self.assertEqual(recipe.link, original_link)  # 断言链接未更新
        self.assertEqual(recipe.user, self.user)  # 断言食谱用户为当前用户

    def test_full_update(self):
        recipe = create_recipe(
            user=self.user,
            title='Sample recipe title',
            time_minutes=22,
            price=Decimal('5.25'),
            description='Sample Description',
            link='http://sample.com/recipe.pdf'
        )

        payload = {
            'title': 'New recipe title',
            'time_minutes': 30,
            'price': Decimal('5.99'),
            'description': 'New Description',
            'link': 'http://sample.com/new-recipe.pdf'
        }

        url = detail_url(recipe.id)  # 获取食谱详情的URL
        res = self.client.put(url, payload)  # 全量更新食谱

        self.assertEqual(res.status_code, status.HTTP_200_OK)  # 断言返回200成功
        recipe.refresh_from_db()
        for k, v in payload.items():
            self.assertEqual(v, getattr(recipe, k))  # 断言返回数据与输入数据一致
        self.assertEqual(recipe.user, self.user)  # 断言食谱用户为当前用户

    def test_update_user_return_error(self):
        new_user = create_user(
            email='user2@example.com',
            password='testpass'
        )  # 创建新用户
        recipe = create_recipe(user=self.user)  # 创建食谱

        payload = {
            'user': new_user.id
        }
        url = detail_url(recipe.id)  # 获取食谱详情的URL
        self.client.patch(url, payload)  # 尝试更新食谱用户

        recipe.refresh_from_db()
        self.assertEqual(recipe.user, self.user)  # 断言食谱用户未更新

    def test_delete_recipe(self):
        recipe = create_recipe(user=self.user)  # 创建食谱
        url = detail_url(recipe.id)  # 获取食谱详情的URL
        res = self.client.delete(url)  # 删除食谱
        # 断言返回204无内容
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        # 断言食谱已删除
        self.assertFalse(Recipe.objects.filter(id=recipe.id).exists())

    def test_recipe_other_users_return_error(self):
        new_user = create_user(
            email='user2@example.com',
            password='testpass'
        )  # 创建新用户
        recipe = create_recipe(user=new_user)  # 创建新用户的食谱

        url = detail_url(recipe.id)  # 获取食谱详情的URL
        res = self.client.get(url)  # 尝试获取其他用户的食谱
        # 断言返回404未找到
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        # 断言食谱仍然存在
        self.assertTrue(Recipe.objects.filter(id=recipe.id).exists())

    def test_create_recipe_with_new_tags(self):
        payload = {
            'title': 'Avocado lime cheesecake',
            'time_minutes': 60,
            'price': Decimal('20.00'),
            'tags': [{'vegan', 'dessert'}, {'gluten-free', 'dessert'}]
        }
        res = self.client.post(RECIPE_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.tags.count(), 2)
        for tag in payload['tags']:
            exists = recipe.tags.filter(
                name=tag['name'],
                user=self.user,
            ).exists()
            self.assertTrue(exists)

    def test_create_recipe_with_existing_tags(self):
        tag_indian = Tag.objects.create(user=self.user, name='Indian')
        payload = {
            'title': 'Indian curry',
            'time_minutes': 20,
            'price': Decimal('7.00'),
            'tags': [
                {'name': 'Indian'},
                {'name': 'Breakfast'}
            ]
        }

        res = self.client.post(RECIPE_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.tags.count(), 2)
        self.assertIn(tag_indian, recipe.tags.all())
        for tag in payload['tags']:
            exist = recipe.tags.filter(
                name=tag['name'],
                user=self.user,
            ).exists()
            self.assertTrue(exist)

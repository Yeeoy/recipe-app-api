# app/recipe/serializers.py
from rest_framework import serializers

from core.models import Recipe


class RecipeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = ('id', 'title', 'time_minutes', 'price', 'link')  # 包含主食字段
        read_only_fields = ('id',)  # id字段只读


class RecipeDetailSerializer(RecipeSerializer):
    class Meta(RecipeSerializer.Meta):
        # 详细序列化器包含描述字段
        fields = RecipeSerializer.Meta.fields + ('description',)

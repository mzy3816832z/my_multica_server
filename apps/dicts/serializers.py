"""
字典序列化器
"""
from rest_framework import serializers
from apps.dicts.models import SystemDict


class SystemDictSerializer(serializers.ModelSerializer):
    """
    系统字典序列化器
    """
    class Meta:
        model = SystemDict
        fields = ['id', 'category', 'code', 'label', 'sort', 'is_active']

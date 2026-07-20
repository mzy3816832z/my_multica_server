"""
行政区划模块：序列化器
"""
from rest_framework import serializers
from apps.districts.models import District


class DistrictSerializer(serializers.ModelSerializer):
    """
    行政区划序列化器
    """
    class Meta:
        model = District
        fields = ['id', 'name', 'level', 'code', 'sort', 'parent', 'created_at', 'updated_at']


class DistrictListSerializer(serializers.ModelSerializer):
    """
    行政区划列表序列化器（精简字段）
    """
    class Meta:
        model = District
        fields = ['id', 'name', 'level', 'code', 'sort', 'parent']

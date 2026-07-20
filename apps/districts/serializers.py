"""
行政区划序列化器
"""
from rest_framework import serializers
from apps.districts.models import District


class DistrictSerializer(serializers.ModelSerializer):
    """
    行政区划序列化器
    """
    class Meta:
        model = District
        fields = ['id', 'name', 'level', 'code', 'sort', 'parent']

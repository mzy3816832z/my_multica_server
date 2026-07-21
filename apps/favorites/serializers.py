"""
收藏模块序列化器
"""
from rest_framework import serializers


class FavoriteCreateSerializer(serializers.Serializer):
    """添加收藏请求序列化器"""
    apartment_id = serializers.IntegerField(min_value=1, help_text='公寓 ID')


class FavoriteCreateResponseSerializer(serializers.Serializer):
    """添加收藏响应序列化器"""
    id = serializers.IntegerField(help_text='收藏记录 ID')
    apartment_id = serializers.IntegerField(help_text='公寓 ID')
    created_at = serializers.DateTimeField(help_text='收藏时间')


class FavoriteListItemSerializer(serializers.Serializer):
    """收藏列表项序列化器"""
    id = serializers.IntegerField(help_text='收藏记录 ID')
    apartment_id = serializers.IntegerField(help_text='公寓 ID')
    apartment_name = serializers.CharField(help_text='公寓名称')
    cover_image = serializers.CharField(help_text='公寓总览图 URL')
    district_name = serializers.CharField(help_text='行政区名称')
    street_name = serializers.CharField(help_text='街道/镇名称')
    min_monthly_rent = serializers.IntegerField(help_text='最低月租金（元）', allow_null=True)
    created_at = serializers.DateTimeField(help_text='收藏时间')

"""
通用字段封装
"""
from rest_framework import serializers


class TimestampField(serializers.IntegerField):
    """
    Unix 时间戳字段（秒级整数）

    将 datetime 对象序列化为 Unix 时间戳整数，
    解决 Windows 平台下 DRF DATETIME_FORMAT='%s' 不兼容的问题。
    """

    def to_representation(self, value):
        if value:
            return int(value.timestamp())
        return None

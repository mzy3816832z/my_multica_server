"""
消息模块序列化器
"""
from rest_framework import serializers
from core.fields import TimestampField


class MessageListItemSerializer(serializers.Serializer):
    """站内信列表项序列化器"""
    id = serializers.IntegerField(help_text='消息 ID')
    type = serializers.CharField(max_length=30, help_text='消息类型')
    type_display = serializers.SerializerMethodField(help_text='消息类型展示')
    title = serializers.CharField(max_length=100, help_text='标题')
    content = serializers.CharField(help_text='内容')
    related_apartment_id = serializers.IntegerField(help_text='关联房源 ID')
    related_audit_id = serializers.IntegerField(help_text='关联审核单 ID', allow_null=True)
    is_read = serializers.BooleanField(help_text='是否已读')
    created_at = TimestampField(help_text='创建时间')

    def get_type_display(self, obj):
        return obj.get_type_display()


class MessageReadSerializer(serializers.Serializer):
    """标记已读响应序列化器"""
    id = serializers.IntegerField(help_text='消息 ID')
    is_read = serializers.BooleanField(help_text='是否已读')


class MessageUnreadCountSerializer(serializers.Serializer):
    """未读数响应序列化器"""
    unread_count = serializers.IntegerField(help_text='未读消息数量')

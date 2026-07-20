"""
审核模块序列化器
"""
from rest_framework import serializers


class AuditListItemSerializer(serializers.Serializer):
    """审核列表项序列化器"""
    id = serializers.IntegerField(help_text='审核单 ID')
    apartment_id = serializers.IntegerField(help_text='关联房源 ID')
    apartment_name = serializers.SerializerMethodField(help_text='公寓名称')
    type = serializers.CharField(max_length=30, help_text='审核类型')
    type_display = serializers.SerializerMethodField(help_text='审核类型展示')
    status = serializers.CharField(max_length=30, help_text='审核状态')
    status_display = serializers.SerializerMethodField(help_text='审核状态展示')
    landlord_name = serializers.SerializerMethodField(help_text='商家名称')
    created_at = serializers.DateTimeField(help_text='提交时间')
    updated_at = serializers.DateTimeField(help_text='更新时间')

    def get_apartment_name(self, obj):
        return obj.apartment.name if obj.apartment else None

    def get_type_display(self, obj):
        return obj.get_type_display()

    def get_status_display(self, obj):
        return obj.get_status_display()

    def get_landlord_name(self, obj):
        landlord = obj.apartment.landlord if obj.apartment else None
        return landlord.username or landlord.phone if landlord else None


class AuditDetailSerializer(serializers.Serializer):
    """审核详情序列化器"""
    id = serializers.IntegerField(help_text='审核单 ID')
    apartment_id = serializers.IntegerField(help_text='关联房源 ID')
    apartment_name = serializers.SerializerMethodField(help_text='公寓名称')
    type = serializers.CharField(max_length=30, help_text='审核类型')
    type_display = serializers.SerializerMethodField(help_text='审核类型展示')
    status = serializers.CharField(max_length=30, help_text='审核状态')
    status_display = serializers.SerializerMethodField(help_text='审核状态展示')
    submitted_data = serializers.JSONField(help_text='提交时完整房源快照')
    original_data = serializers.JSONField(help_text='原房源快照（变更审核时）', required=False)
    changed_fields = serializers.JSONField(help_text='变更字段名列表', required=False)
    reject_reason = serializers.CharField(max_length=500, help_text='驳回原因', required=False)
    reviewer_id = serializers.IntegerField(help_text='审核管理员 ID', allow_null=True)
    created_at = serializers.DateTimeField(help_text='提交时间')
    updated_at = serializers.DateTimeField(help_text='更新时间')

    def get_apartment_name(self, obj):
        return obj.apartment.name if obj.apartment else None

    def get_type_display(self, obj):
        return obj.get_type_display()

    def get_status_display(self, obj):
        return obj.get_status_display()


class AuditApproveSerializer(serializers.Serializer):
    """审核通过请求序列化器（无额外字段，仅用于文档）"""
    pass


class AuditRejectSerializer(serializers.Serializer):
    """审核驳回请求序列化器"""
    reject_reason = serializers.CharField(
        max_length=500,
        min_length=1,
        help_text='驳回原因（必填，1-500 字）',
    )

    def validate_reject_reason(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError('驳回原因不能为空')
        return value


class AuditActionResponseSerializer(serializers.Serializer):
    """审核操作响应序列化器"""
    audit_id = serializers.IntegerField(help_text='审核单 ID')
    apartment_id = serializers.IntegerField(help_text='关联房源 ID')
    action = serializers.CharField(help_text='操作类型：approve / reject')
    status = serializers.CharField(help_text='审核单最新状态')

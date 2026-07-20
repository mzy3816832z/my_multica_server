"""
房源模块序列化器
"""
from rest_framework import serializers
from core.exceptions import BusinessException
from apps.apartments.models import Apartment, RoomType, RentalPlan


class RentalPlanSerializer(serializers.Serializer):
    """租期租金方案序列化器（输入/输出）"""
    lease_term = serializers.CharField(max_length=30, help_text='租期编码')
    monthly_rent = serializers.IntegerField(min_value=1, help_text='月租金（元），必须大于0')
    payment_method = serializers.CharField(max_length=30, help_text='支付方式编码')


class RoomTypeSerializer(serializers.Serializer):
    """房型序列化器（输入/输出）"""
    name = serializers.CharField(max_length=50, help_text='房型名称')
    images = serializers.ListField(
        child=serializers.URLField(),
        help_text='房型图片 URL 数组',
    )
    facilities = serializers.ListField(
        child=serializers.CharField(max_length=30),
        default=list,
        help_text='设施编码数组',
    )
    layout_type = serializers.CharField(max_length=30, help_text='户型编码')
    window_type = serializers.CharField(max_length=30, help_text='内外窗编码')
    orientation = serializers.CharField(max_length=30, help_text='朝向编码')
    floor = serializers.IntegerField(min_value=1, help_text='楼层，必须≥1')
    sort = serializers.IntegerField(default=0, help_text='展示排序')
    rental_plans = RentalPlanSerializer(many=True, help_text='租期租金方案列表')

    def validate_images(self, value):
        """校验房型图片数量 ≤5 张"""
        if len(value) > 5:
            raise serializers.ValidationError('房型图片最多 5 张')
        return value

    def validate_rental_plans(self, value):
        """校验租期租金方案 ≥1 组"""
        if not value or len(value) < 1:
            raise serializers.ValidationError('每个房型至少需 1 组租期租金方案')
        return value


class ApartmentCreateSerializer(serializers.Serializer):
    """公寓发布请求序列化器"""
    name = serializers.CharField(
        max_length=50,
        min_length=2,
        help_text='公寓名称（2-50 字）',
    )
    cover_image = serializers.URLField(help_text='公寓总览图 URL')
    description = serializers.CharField(
        max_length=500,
        help_text='公寓描述（≤500 字）',
    )
    district_id = serializers.IntegerField(help_text='行政区 ID')
    street_id = serializers.IntegerField(help_text='街道/镇 ID')
    detail_address = serializers.CharField(
        max_length=200,
        help_text='详细门牌号',
    )
    contact_phone = serializers.CharField(
        max_length=11,
        min_length=11,
        help_text='联系电话（11 位手机号）',
    )
    room_types = RoomTypeSerializer(
        many=True,
        help_text='房型列表（至少 1 组）',
    )

    def validate_room_types(self, value):
        """校验至少 1 组房型"""
        if not value or len(value) < 1:
            raise serializers.ValidationError('至少需添加 1 组房型')
        return value

    def validate(self, attrs):
        """额外校验：行政区与街道有效性"""
        from apps.districts.models import District

        district_id = attrs.get('district_id')
        street_id = attrs.get('street_id')

        # 校验 district_id 是否为有效行政区（level=1）
        try:
            district = District.objects.get(id=district_id, level=1)
        except District.DoesNotExist:
            raise serializers.ValidationError({'district_id': '无效的行政区 ID'})

        # 校验 street_id 是否为有效街道/镇（level=2）且属于该行政区
        try:
            street = District.objects.get(id=street_id, level=2, parent=district)
        except District.DoesNotExist:
            raise serializers.ValidationError({'street_id': '无效的街道/镇 ID，或不在该行政区内'})

        return attrs


class ApartmentResponseSerializer(serializers.Serializer):
    """公寓发布响应序列化器"""
    apartment_id = serializers.IntegerField(help_text='公寓 ID')
    audit_id = serializers.IntegerField(help_text='审核记录 ID')

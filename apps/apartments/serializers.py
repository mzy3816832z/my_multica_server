"""
房源模块序列化器
"""
from rest_framework import serializers


class RentalPlanSerializer(serializers.Serializer):
    """租期租金方案序列化器（输入/输出）"""
    lease_term = serializers.CharField(max_length=30, help_text='租期编码')
    monthly_rent = serializers.IntegerField(min_value=1, help_text='月租金（元），必须大于0')
    payment_method = serializers.CharField(max_length=30, help_text='支付方式编码')


class RoomTypeSerializer(serializers.Serializer):
    """房型序列化器（输入/输出）"""
    name = serializers.CharField(max_length=50, help_text='房型名称')
    images = serializers.ListField(
        child=serializers.CharField(max_length=500),
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
        min_length=1,
        help_text='公寓名称（1-50 字）',
    )
    cover_image = serializers.CharField(max_length=500, help_text='公寓总览图 URL')
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
            District.objects.get(id=street_id, level=2, parent=district)
        except District.DoesNotExist:
            raise serializers.ValidationError({'street_id': '无效的街道/镇 ID，或不在该行政区内'})

        return attrs


class ApartmentUpdateSerializer(serializers.Serializer):
    """公寓编辑请求序列化器"""
    name = serializers.CharField(
        max_length=50,
        min_length=1,
        required=False,
        help_text='公寓名称（1-50 字）',
    )
    cover_image = serializers.CharField(max_length=500, required=False, help_text='公寓总览图 URL')
    description = serializers.CharField(
        max_length=500,
        required=False,
        help_text='公寓描述（≤500 字）',
    )
    district_id = serializers.IntegerField(required=False, help_text='行政区 ID')
    street_id = serializers.IntegerField(required=False, help_text='街道/镇 ID')
    detail_address = serializers.CharField(
        max_length=200,
        required=False,
        help_text='详细门牌号',
    )
    contact_phone = serializers.CharField(
        max_length=11,
        min_length=11,
        required=False,
        help_text='联系电话（11 位手机号）',
    )
    room_types = RoomTypeSerializer(
        many=True,
        required=False,
        help_text='房型列表',
    )

    def validate(self, attrs):
        """额外校验：行政区与街道有效性"""
        from apps.districts.models import District

        district_id = attrs.get('district_id')
        street_id = attrs.get('street_id')

        if street_id is not None:
            try:
                street = District.objects.get(id=street_id, level=2)
            except District.DoesNotExist:
                raise serializers.ValidationError({'street_id': '无效的街道/镇 ID'})

            if district_id is not None and street.parent_id != district_id:
                raise serializers.ValidationError({'street_id': '街道/镇不在该行政区内'})

        if district_id is not None:
            try:
                District.objects.get(id=district_id, level=1)
            except District.DoesNotExist:
                raise serializers.ValidationError({'district_id': '无效的行政区 ID'})

        return attrs


class MerchantApartmentListSerializer(serializers.Serializer):
    """商家已上架房源列表序列化器"""
    id = serializers.IntegerField(help_text='公寓 ID')
    name = serializers.CharField(max_length=50, help_text='公寓名称')
    cover_image = serializers.CharField(max_length=500, help_text='公寓总览图 URL')
    district_name = serializers.SerializerMethodField(help_text='行政区名称')
    street_name = serializers.SerializerMethodField(help_text='街道/镇名称')
    detail_address = serializers.CharField(max_length=200, help_text='详细门牌号')
    min_monthly_rent = serializers.IntegerField(help_text='最低月租金（元）')
    status = serializers.CharField(max_length=30, help_text='房源状态')
    created_at = serializers.DateTimeField(help_text='创建时间')
    updated_at = serializers.DateTimeField(help_text='更新时间')

    def get_district_name(self, obj):
        return obj.district.name if obj.district else None

    def get_street_name(self, obj):
        return obj.street.name if obj.street else None


class MerchantApartmentDetailSerializer(serializers.Serializer):
    """商家自有房源详情序列化器"""
    id = serializers.IntegerField(help_text='公寓 ID')
    name = serializers.CharField(max_length=50, help_text='公寓名称')
    cover_image = serializers.CharField(max_length=500, help_text='公寓总览图 URL')
    description = serializers.CharField(help_text='公寓描述')
    district_id = serializers.IntegerField(help_text='行政区 ID')
    district_name = serializers.SerializerMethodField(help_text='行政区名称')
    street_id = serializers.IntegerField(help_text='街道/镇 ID')
    street_name = serializers.SerializerMethodField(help_text='街道/镇名称')
    detail_address = serializers.CharField(max_length=200, help_text='详细门牌号')
    contact_phone = serializers.CharField(max_length=11, help_text='联系电话')
    min_monthly_rent = serializers.IntegerField(help_text='最低月租金（元）')
    status = serializers.CharField(max_length=30, help_text='房源状态')
    created_at = serializers.DateTimeField(help_text='创建时间')
    updated_at = serializers.DateTimeField(help_text='更新时间')
    room_types = serializers.SerializerMethodField(help_text='房型列表')
    pending_audit = serializers.SerializerMethodField(help_text='是否有待审核变更')

    def get_district_name(self, obj):
        return obj.district.name if obj.district else None

    def get_street_name(self, obj):
        return obj.street.name if obj.street else None

    def get_room_types(self, obj):
        room_types = obj.room_types.all().order_by('sort', 'id')
        return RoomTypeListSerializer(room_types, many=True).data

    def get_pending_audit(self, obj):
        return obj.audit_records.filter(
            type='change_review',
            status='pending',
            deleted_at__isnull=True,
        ).exists()


class MerchantApartmentUpdateResponseSerializer(serializers.Serializer):
    """商家房源编辑响应序列化器"""
    apartment_id = serializers.IntegerField(help_text='公寓 ID')
    audit_id = serializers.IntegerField(help_text='审核记录 ID（直接更新时为 null）', allow_null=True)
    updated = serializers.BooleanField(help_text='是否直接更新')


class MerchantApartmentDeleteResponseSerializer(serializers.Serializer):
    """商家房源删除响应序列化器"""
    apartment_id = serializers.IntegerField(help_text='公寓 ID')
    deleted = serializers.BooleanField(help_text='是否删除成功')


class ApartmentResponseSerializer(serializers.Serializer):
    """公寓发布响应序列化器"""
    apartment_id = serializers.IntegerField(help_text='公寓 ID')
    audit_id = serializers.IntegerField(help_text='审核记录 ID')


# ============================================================
# 公共房源列表与详情序列化器（新增）
# ============================================================

class RentalPlanListSerializer(serializers.Serializer):
    """租期租金方案列表展示序列化器"""
    id = serializers.IntegerField(help_text='租金方案 ID')
    lease_term = serializers.CharField(max_length=30, help_text='租期编码')
    monthly_rent = serializers.IntegerField(help_text='月租金（元）')
    payment_method = serializers.CharField(max_length=30, help_text='支付方式编码')


class RoomTypeListSerializer(serializers.Serializer):
    """房型列表展示序列化器（用于房源详情内嵌）"""
    id = serializers.IntegerField(help_text='房型 ID')
    name = serializers.CharField(max_length=50, help_text='房型名称')
    images = serializers.ListField(
        child=serializers.CharField(max_length=500),
        help_text='房型图片 URL 数组',
    )
    facilities = serializers.ListField(
        child=serializers.CharField(max_length=30),
        help_text='设施编码数组',
    )
    layout_type = serializers.CharField(max_length=30, help_text='户型编码')
    window_type = serializers.CharField(max_length=30, help_text='内外窗编码')
    orientation = serializers.CharField(max_length=30, help_text='朝向编码')
    floor = serializers.IntegerField(help_text='楼层')
    sort = serializers.IntegerField(help_text='展示排序')
    min_monthly_rent = serializers.SerializerMethodField(help_text='该房型最低月租金')

    def get_min_monthly_rent(self, obj):
        """计算该房型最低月租金"""
        rents = [rp.monthly_rent for rp in obj.rental_plans.all() if rp.monthly_rent is not None]
        return min(rents) if rents else None


class RoomTypeDetailSerializer(serializers.Serializer):
    """户型详情展示序列化器"""
    id = serializers.IntegerField(help_text='房型 ID')
    name = serializers.CharField(max_length=50, help_text='房型名称')
    images = serializers.ListField(
        child=serializers.CharField(max_length=500),
        help_text='房型图片 URL 数组',
    )
    facilities = serializers.ListField(
        child=serializers.CharField(max_length=30),
        help_text='设施编码数组',
    )
    layout_type = serializers.CharField(max_length=30, help_text='户型编码')
    window_type = serializers.CharField(max_length=30, help_text='内外窗编码')
    orientation = serializers.CharField(max_length=30, help_text='朝向编码')
    floor = serializers.IntegerField(help_text='楼层')
    sort = serializers.IntegerField(help_text='展示排序')
    rental_plans = RentalPlanListSerializer(many=True, help_text='租期租金方案列表')
    apartment = serializers.SerializerMethodField(help_text='所属公寓简要信息')

    def get_apartment(self, obj):
        """返回所属公寓简要信息"""
        apartment = obj.apartment
        return {
            'id': apartment.id,
            'name': apartment.name,
            'cover_image': apartment.cover_image,
        }


class ApartmentListItemSerializer(serializers.Serializer):
    """房源列表卡片序列化器"""
    id = serializers.IntegerField(help_text='公寓 ID')
    name = serializers.CharField(max_length=50, help_text='公寓名称')
    cover_image = serializers.CharField(max_length=500, help_text='公寓总览图 URL')
    district_name = serializers.SerializerMethodField(help_text='行政区名称')
    street_name = serializers.SerializerMethodField(help_text='街道/镇名称')
    min_monthly_rent = serializers.IntegerField(help_text='最低月租金（元）')
    is_favorited = serializers.SerializerMethodField(help_text='当前用户是否已收藏')

    def get_district_name(self, obj):
        return obj.district.name if obj.district else None

    def get_street_name(self, obj):
        return obj.street.name if obj.street else None

    def get_is_favorited(self, obj):
        """若用户已登录，检查是否已收藏该房源"""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        from apps.favorites.models import Favorite
        return Favorite.objects.filter(user=request.user, apartment=obj).exists()


class ApartmentDetailSerializer(serializers.Serializer):
    """房源详情序列化器"""
    id = serializers.IntegerField(help_text='公寓 ID')
    name = serializers.CharField(max_length=50, help_text='公寓名称')
    cover_image = serializers.CharField(max_length=500, help_text='公寓总览图 URL')
    description = serializers.CharField(help_text='公寓描述')
    district_name = serializers.SerializerMethodField(help_text='行政区名称')
    street_name = serializers.SerializerMethodField(help_text='街道/镇名称')
    detail_address = serializers.CharField(max_length=200, help_text='详细门牌号')
    contact_phone = serializers.CharField(max_length=11, help_text='联系电话')
    min_monthly_rent = serializers.IntegerField(help_text='最低月租金（元）')
    is_favorited = serializers.SerializerMethodField(help_text='当前用户是否已收藏')
    room_types = serializers.SerializerMethodField(help_text='房型卡片列表')

    def get_district_name(self, obj):
        return obj.district.name if obj.district else None

    def get_street_name(self, obj):
        return obj.street.name if obj.street else None

    def get_is_favorited(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        from apps.favorites.models import Favorite
        return Favorite.objects.filter(user=request.user, apartment=obj).exists()

    def get_room_types(self, obj):
        room_types = obj.room_types.all().order_by('sort', 'id')
        return RoomTypeListSerializer(room_types, many=True).data

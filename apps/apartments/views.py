"""
房源模块视图：商家发布房源接口
"""
import logging
from django.db import transaction
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema

from core.response import unified_response, ErrorCode
from core.exceptions import BusinessException, ParamErrorException
from core.permissions import IsLandlord
from apps.apartments.models import Apartment, RoomType, RentalPlan
from apps.apartments.serializers import (
    ApartmentCreateSerializer,
    ApartmentResponseSerializer,
)
from apps.audits.models import AuditRecord

logger = logging.getLogger('apps')


@extend_schema(
    request=ApartmentCreateSerializer,
    responses={200: ApartmentResponseSerializer},
    summary='商家发布房源',
    description='商家发布房源并提交首次审核。校验公寓基础信息、至少 1 组房型、房型图片 ≤5 张、租期租金方案 ≥1 组；保存公寓状态为 pending_first_review 并创建 first_review 审核记录。',
    tags=['商家房源'],
)
@api_view(['POST'])
@permission_classes([IsAuthenticated, IsLandlord])
def create_apartment(request):
    """
    POST /api/v1/merchant/apartments
    商家发布房源
    """
    serializer = ApartmentCreateSerializer(data=request.data)
    if not serializer.is_valid():
        # 提取第一个错误信息，返回 400002
        first_msg = _extract_first_error(serializer.errors)
        raise BusinessException(first_msg, code=ErrorCode.BUSINESS_ERROR)

    data = serializer.validated_data
    landlord = request.user

    with transaction.atomic():
        # 1. 创建公寓
        apartment = Apartment.objects.create(
            landlord=landlord,
            name=data['name'],
            cover_image=data['cover_image'],
            description=data['description'],
            district_id=data['district_id'],
            street_id=data['street_id'],
            detail_address=data['detail_address'],
            contact_phone=data['contact_phone'],
            status='pending_first_review',
            min_monthly_rent=None,
        )

        # 2. 创建房型与租金方案，计算最低月租金
        global_min_rent = None
        for rt_data in data['room_types']:
            room_type = RoomType.objects.create(
                apartment=apartment,
                name=rt_data['name'],
                images=rt_data['images'],
                facilities=rt_data.get('facilities', []),
                layout_type=rt_data['layout_type'],
                window_type=rt_data['window_type'],
                orientation=rt_data['orientation'],
                floor=rt_data['floor'],
                sort=rt_data.get('sort', 0),
            )

            for rp_data in rt_data['rental_plans']:
                RentalPlan.objects.create(
                    room_type=room_type,
                    lease_term=rp_data['lease_term'],
                    monthly_rent=rp_data['monthly_rent'],
                    payment_method=rp_data['payment_method'],
                )
                if global_min_rent is None or rp_data['monthly_rent'] < global_min_rent:
                    global_min_rent = rp_data['monthly_rent']

        # 3. 更新公寓最低月租金缓存
        if global_min_rent is not None:
            apartment.min_monthly_rent = global_min_rent
            apartment.save(update_fields=['min_monthly_rent'])

        # 4. 构建房源快照 JSON
        submitted_data = _build_apartment_snapshot(apartment)

        # 5. 创建首次审核记录
        audit = AuditRecord.objects.create(
            apartment=apartment,
            type='first_review',
            status='pending',
            submitted_data=submitted_data,
        )

    logger.info(f'[CreateApartment] landlord={landlord.id}, apartment={apartment.id}, audit={audit.id}')

    return unified_response(
        data={
            'apartment_id': apartment.id,
            'audit_id': audit.id,
        },
        code=ErrorCode.SUCCESS,
    )


def _extract_first_error(errors):
    """
    从 serializer.errors 中提取第一个错误信息字符串
    """
    if isinstance(errors, dict):
        for key in errors:
            val = errors[key]
            if isinstance(val, list):
                return str(val[0])
            elif isinstance(val, dict):
                return _extract_first_error(val)
            else:
                return str(val)
    elif isinstance(errors, list):
        return str(errors[0])
    return str(errors)


def _build_apartment_snapshot(apartment):
    """
    构建房源完整快照 JSON，包含公寓、房型、租金方案
    """
    room_types_data = []
    for rt in apartment.room_types.all():
        plans = []
        for rp in rt.rental_plans.all():
            plans.append({
                'lease_term': rp.lease_term,
                'monthly_rent': rp.monthly_rent,
                'payment_method': rp.payment_method,
            })
        room_types_data.append({
            'name': rt.name,
            'images': rt.images,
            'facilities': rt.facilities,
            'layout_type': rt.layout_type,
            'window_type': rt.window_type,
            'orientation': rt.orientation,
            'floor': rt.floor,
            'sort': rt.sort,
            'rental_plans': plans,
        })

    return {
        'name': apartment.name,
        'cover_image': apartment.cover_image,
        'description': apartment.description,
        'district_id': apartment.district_id,
        'street_id': apartment.street_id,
        'detail_address': apartment.detail_address,
        'contact_phone': apartment.contact_phone,
        'room_types': room_types_data,
    }

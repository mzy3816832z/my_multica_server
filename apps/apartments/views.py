"""
房源模块视图：公共房源列表与详情、商家发布/管理房源接口
"""
import copy
import logging
from django.db import transaction
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from drf_spectacular.utils import extend_schema

from django.utils import timezone
from core.response import unified_response, ErrorCode
from core.exceptions import BusinessException, NotFoundException
from core.permissions import IsLandlord
from core.pagination import StandardPagination
from apps.apartments.models import Apartment, RoomType, RentalPlan
from apps.apartments.serializers import (
    ApartmentCreateSerializer,
    ApartmentResponseSerializer,
    ApartmentListItemSerializer,
    ApartmentDetailSerializer,
    RoomTypeDetailSerializer,
    ApartmentUpdateSerializer,
    MerchantApartmentListSerializer,
    MerchantApartmentDetailSerializer,
    MerchantApartmentUpdateResponseSerializer,
    MerchantApartmentDeleteResponseSerializer,
)
from apps.audits.models import AuditRecord

logger = logging.getLogger('apps')


# ============================================================
# 公共房源接口（公开访问）
# ============================================================

@extend_schema(
    request=None,
    responses={200: ApartmentListItemSerializer(many=True)},
    summary='公共房源列表',
    description='仅展示已上架（published）房源，支持组合筛选与分页。筛选条件可叠加，结果按审核通过时间（updated_at）倒序。',
    tags=['公共房源'],
    parameters=[
        {'name': 'keyword', 'in': 'query', 'schema': {'type': 'string'}, 'description': '公寓名称关键词'},
        {'name': 'district_id', 'in': 'query', 'schema': {'type': 'integer'}, 'description': '行政区 ID'},
        {'name': 'street_id', 'in': 'query', 'schema': {'type': 'integer'}, 'description': '街道/镇 ID'},
        {'name': 'layout_type', 'in': 'query', 'schema': {'type': 'string'}, 'description': '户型编码'},
        {'name': 'lease_term', 'in': 'query', 'schema': {'type': 'string'}, 'description': '租期编码'},
        {'name': 'min_price', 'in': 'query', 'schema': {'type': 'integer'}, 'description': '最低月租金'},
        {'name': 'max_price', 'in': 'query', 'schema': {'type': 'integer'}, 'description': '最高月租金'},
        {'name': 'page', 'in': 'query', 'schema': {'type': 'integer'}, 'description': '页码，默认 1'},
        {'name': 'page_size', 'in': 'query', 'schema': {'type': 'integer'}, 'description': '每页条数，默认 10，最大 100'},
    ],
)
@api_view(['GET'])
@permission_classes([AllowAny])
def apartment_list(request):
    """
    GET /api/v1/apartments
    公共房源列表（仅 published）
    """
    queryset = Apartment.objects.filter(status='published').order_by('-updated_at')

    # 关键词搜索（公寓名称）
    keyword = request.query_params.get('keyword')
    if keyword:
        queryset = queryset.filter(name__icontains=keyword)

    # 行政区筛选
    district_id = request.query_params.get('district_id')
    if district_id:
        try:
            queryset = queryset.filter(district_id=int(district_id))
        except ValueError:
            pass

    # 街道筛选
    street_id = request.query_params.get('street_id')
    if street_id:
        try:
            queryset = queryset.filter(street_id=int(street_id))
        except ValueError:
            pass

    # 户型筛选（通过关联房型）
    layout_type = request.query_params.get('layout_type')
    if layout_type:
        queryset = queryset.filter(room_types__layout_type=layout_type).distinct()

    # 租期筛选（通过关联房型→租金方案）
    lease_term = request.query_params.get('lease_term')
    if lease_term:
        queryset = queryset.filter(
            room_types__rental_plans__lease_term=lease_term
        ).distinct()

    # 价格区间筛选（基于 min_monthly_rent）
    min_price = request.query_params.get('min_price')
    max_price = request.query_params.get('max_price')
    if min_price:
        try:
            queryset = queryset.filter(min_monthly_rent__gte=int(min_price))
        except ValueError:
            pass
    if max_price:
        try:
            queryset = queryset.filter(min_monthly_rent__lte=int(max_price))
        except ValueError:
            pass

    # 分页
    paginator = StandardPagination()
    page = paginator.paginate_queryset(queryset, request)
    serializer = ApartmentListItemSerializer(
        page, many=True, context={'request': request}
    )
    return paginator.get_paginated_response(serializer.data)


@extend_schema(
    request=None,
    responses={200: ApartmentDetailSerializer},
    summary='房源详情',
    description='返回完整公寓信息、房型卡片列表及当前用户收藏状态（已登录时）。',
    tags=['公共房源'],
    parameters=[
        {'name': 'id', 'in': 'path', 'schema': {'type': 'integer'}, 'description': '公寓 ID'},
    ],
)
@api_view(['GET'])
@permission_classes([AllowAny])
def apartment_detail(request, id):
    """
    GET /api/v1/apartments/{id}
    房源详情
    """
    try:
        apartment = Apartment.objects.get(id=id, status='published')
    except Apartment.DoesNotExist:
        raise NotFoundException('房源不存在或未上架')

    serializer = ApartmentDetailSerializer(apartment, context={'request': request})
    return unified_response(data=serializer.data)


@extend_schema(
    request=None,
    responses={200: RoomTypeDetailSerializer(many=True)},
    summary='房源下所有房型',
    description='获取指定房源下的所有房型详情（含租金方案）。',
    tags=['公共房源'],
    parameters=[
        {'name': 'id', 'in': 'path', 'schema': {'type': 'integer'}, 'description': '公寓 ID'},
    ],
)
@api_view(['GET'])
@permission_classes([AllowAny])
def apartment_room_types(request, id):
    """
    GET /api/v1/apartments/{id}/room-types
    房源下所有房型
    """
    try:
        apartment = Apartment.objects.get(id=id, status='published')
    except Apartment.DoesNotExist:
        raise NotFoundException('房源不存在或未上架')

    room_types = apartment.room_types.all().order_by('sort', 'id')
    # 预加载租金方案，避免 N+1
    room_types = room_types.prefetch_related('rental_plans')
    serializer = RoomTypeDetailSerializer(room_types, many=True)
    return unified_response(data=serializer.data)


@extend_schema(
    request=None,
    responses={200: RoomTypeDetailSerializer},
    summary='户型详情',
    description='获取指定户型详情，包含完整租金方案及所属公寓简要信息。',
    tags=['公共房源'],
    parameters=[
        {'name': 'id', 'in': 'path', 'schema': {'type': 'integer'}, 'description': '户型 ID'},
    ],
)
@api_view(['GET'])
@permission_classes([AllowAny])
def room_type_detail(request, id):
    """
    GET /api/v1/room-types/{id}
    户型详情
    """
    try:
        room_type = RoomType.objects.get(id=id)
    except RoomType.DoesNotExist:
        raise NotFoundException('户型不存在')

    # 校验所属公寓是否已上架
    if room_type.apartment.status != 'published':
        raise NotFoundException('房源不存在或未上架')

    # 预加载租金方案
    room_type.rental_plans.all()  # prefetch 已在序列化器中通过 context 控制，这里直接查
    serializer = RoomTypeDetailSerializer(room_type)
    return unified_response(data=serializer.data)


# ============================================================
# 商家发布房源接口（已有）
# ============================================================

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


# ============================================================
# 商家已上架房源管理接口（新增）
# ============================================================

@extend_schema(
    request=None,
    responses={200: MerchantApartmentListSerializer(many=True)},
    summary='商家已上架房源列表',
    description='返回当前登录商家所有已上架（published）的房源列表，支持分页。',
    tags=['商家房源'],
    parameters=[
        {'name': 'page', 'in': 'query', 'schema': {'type': 'integer'}, 'description': '页码，默认 1'},
        {'name': 'page_size', 'in': 'query', 'schema': {'type': 'integer'}, 'description': '每页条数，默认 10，最大 100'},
    ],
)
@api_view(['GET'])
@permission_classes([IsAuthenticated, IsLandlord])
def merchant_apartment_list(request):
    """
    GET /api/v1/merchant/apartments
    商家已上架房源列表
    """
    landlord = request.user
    queryset = Apartment.objects.filter(
        landlord=landlord,
        status='published',
    ).order_by('-updated_at')

    paginator = StandardPagination()
    page = paginator.paginate_queryset(queryset, request)
    serializer = MerchantApartmentListSerializer(page, many=True)
    return paginator.get_paginated_response(serializer.data)


@extend_schema(
    request=None,
    responses={200: MerchantApartmentDetailSerializer},
    summary='商家自有房源详情',
    description='获取当前商家指定房源的完整详情，含房型、租金方案及待审核状态。',
    tags=['商家房源'],
    parameters=[
        {'name': 'id', 'in': 'path', 'schema': {'type': 'integer'}, 'description': '公寓 ID'},
    ],
)
@api_view(['GET'])
@permission_classes([IsAuthenticated, IsLandlord])
def merchant_apartment_detail(request, id):
    """
    GET /api/v1/merchant/apartments/{id}
    商家自有房源详情
    """
    landlord = request.user
    try:
        apartment = Apartment.objects.get(id=id, landlord=landlord)
    except Apartment.DoesNotExist:
        raise NotFoundException('房源不存在')

    serializer = MerchantApartmentDetailSerializer(apartment)
    return unified_response(data=serializer.data)


@extend_schema(
    request=ApartmentUpdateSerializer,
    responses={200: MerchantApartmentUpdateResponseSerializer},
    summary='商家编辑房源',
    description=(
        '编辑商家自有房源。若 name、district_id、street_id、detail_address '
        '任一字段变化，则生成 change_review 审核单，原房源仍 published；'
        '否则直接更新房源及关联房型。'
    ),
    tags=['商家房源'],
    parameters=[
        {'name': 'id', 'in': 'path', 'schema': {'type': 'integer'}, 'description': '公寓 ID'},
    ],
)
@api_view(['PUT'])
@permission_classes([IsAuthenticated, IsLandlord])
def merchant_apartment_update(request, id):
    """
    PUT /api/v1/merchant/apartments/{id}
    商家编辑房源
    """
    landlord = request.user
    try:
        apartment = Apartment.objects.get(id=id, landlord=landlord)
    except Apartment.DoesNotExist:
        raise NotFoundException('房源不存在')

    serializer = ApartmentUpdateSerializer(data=request.data)
    if not serializer.is_valid():
        first_msg = _extract_first_error(serializer.errors)
        raise BusinessException(first_msg, code=ErrorCode.BUSINESS_ERROR)

    data = serializer.validated_data

    # 判断关键字段是否变化
    KEY_FIELDS = ['name', 'district_id', 'street_id', 'detail_address']
    key_changed = False
    for field in KEY_FIELDS:
        if field in data:
            current_val = getattr(apartment, field)
            if current_val != data[field]:
                key_changed = True
                break

    # 构建原房源快照（用于审核记录）
    original_data = _build_apartment_snapshot(apartment)

    with transaction.atomic():
        if key_changed:
            # 生成变更审核单，原房源保持 published
            submitted_data = copy.deepcopy(original_data)
            # 将变更应用到 submitted_data 中
            for field in data:
                if field == 'room_types':
                    submitted_data['room_types'] = _build_room_types_from_data(data['room_types'])
                elif field in KEY_FIELDS:
                    submitted_data[field] = data[field]
                elif field == 'cover_image':
                    submitted_data['cover_image'] = data[field]
                elif field == 'description':
                    submitted_data['description'] = data[field]
                elif field == 'contact_phone':
                    submitted_data['contact_phone'] = data[field]

            changed_fields = [f for f in KEY_FIELDS if f in data and getattr(apartment, f) != data[f]]

            audit = AuditRecord.objects.create(
                apartment=apartment,
                type='change_review',
                status='pending',
                submitted_data=submitted_data,
                original_data=original_data,
                changed_fields=changed_fields,
            )

            logger.info(f'[UpdateApartment] change_review created, '
                        f'landlord={landlord.id}, apartment={apartment.id}, audit={audit.id}')

            return unified_response(
                data={
                    'apartment_id': apartment.id,
                    'audit_id': audit.id,
                    'updated': False,
                },
                code=ErrorCode.SUCCESS,
            )
        else:
            # 直接更新房源
            for field in ['name', 'cover_image', 'description', 'contact_phone']:
                if field in data:
                    setattr(apartment, field, data[field])

            if 'district_id' in data:
                apartment.district_id = data['district_id']
            if 'street_id' in data:
                apartment.street_id = data['street_id']
            if 'detail_address' in data:
                apartment.detail_address = data['detail_address']

            apartment.save()

            # 若传了房型数据，全量替换
            if 'room_types' in data:
                # 软删除原有房型（级联软删除租金方案）
                for rt in apartment.room_types.all():
                    rt.delete()

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

                if global_min_rent is not None:
                    apartment.min_monthly_rent = global_min_rent
                    apartment.save(update_fields=['min_monthly_rent'])

            logger.info(f'[UpdateApartment] direct update, '
                        f'landlord={landlord.id}, apartment={apartment.id}')

            return unified_response(
                data={
                    'apartment_id': apartment.id,
                    'audit_id': None,
                    'updated': True,
                },
                code=ErrorCode.SUCCESS,
            )


@extend_schema(
    request=None,
    responses={200: MerchantApartmentDeleteResponseSerializer},
    summary='商家删除房源',
    description='逻辑删除商家自有房源，并同步软删除关联的未批准（pending）审核单。',
    tags=['商家房源'],
    parameters=[
        {'name': 'id', 'in': 'path', 'schema': {'type': 'integer'}, 'description': '公寓 ID'},
    ],
)
@api_view(['DELETE'])
@permission_classes([IsAuthenticated, IsLandlord])
def merchant_apartment_delete(request, id):
    """
    DELETE /api/v1/merchant/apartments/{id}
    商家删除房源
    """
    landlord = request.user
    try:
        apartment = Apartment.objects.get(id=id, landlord=landlord)
    except Apartment.DoesNotExist:
        raise NotFoundException('房源不存在')

    with transaction.atomic():
        # 软删除关联的未批准审核单
        apartment.audit_records.filter(
            status='pending',
            deleted_at__isnull=True,
        ).update(deleted_at=timezone.now())

        # 软删除关联房型（级联软删除租金方案）
        for rt in apartment.room_types.all():
            rt.delete()

        # 软删除房源
        apartment.deleted_at = timezone.now()
        apartment.save(update_fields=['deleted_at'])

    logger.info(f'[DeleteApartment] landlord={landlord.id}, apartment={id}')

    return unified_response(
        data={
            'apartment_id': id,
            'deleted': True,
        },
        code=ErrorCode.SUCCESS,
    )


def _build_room_types_from_data(room_types_data):
    """
    从请求数据构建房型快照列表
    """
    result = []
    for rt_data in room_types_data:
        plans = []
        for rp_data in rt_data['rental_plans']:
            plans.append({
                'lease_term': rp_data['lease_term'],
                'monthly_rent': rp_data['monthly_rent'],
                'payment_method': rp_data['payment_method'],
            })
        result.append({
            'name': rt_data['name'],
            'images': rt_data['images'],
            'facilities': rt_data.get('facilities', []),
            'layout_type': rt_data['layout_type'],
            'window_type': rt_data['window_type'],
            'orientation': rt_data['orientation'],
            'floor': rt_data['floor'],
            'sort': rt_data.get('sort', 0),
            'rental_plans': plans,
        })
    return result


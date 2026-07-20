"""
收藏模块视图：收藏/取消收藏、我的收藏列表
"""
import logging
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema

from core.response import unified_response, ErrorCode
from core.exceptions import NotFoundException, BusinessException
from core.pagination import StandardPagination
from apps.favorites.models import Favorite
from apps.favorites.serializers import (
    FavoriteCreateSerializer,
    FavoriteToggleResponseSerializer,
    FavoriteListItemSerializer,
)
from apps.apartments.models import Apartment

logger = logging.getLogger('apps')


@extend_schema(
    request=FavoriteCreateSerializer,
    responses={200: FavoriteToggleResponseSerializer},
    summary='收藏/取消收藏公寓',
    description='''收藏或取消收藏指定公寓，支持幂等：
- 若当前未收藏，则创建收藏记录，返回 is_favorited=true
- 若当前已收藏，则取消收藏（逻辑删除），返回 is_favorited=false
- 若收藏记录已被逻辑删除，重新收藏时恢复该记录''',
    tags=['收藏'],
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def toggle_favorite(request):
    """
    POST /api/v1/favorites
    收藏/取消收藏公寓（幂等）
    """
    serializer = FavoriteCreateSerializer(data=request.data)
    if not serializer.is_valid():
        first_msg = _extract_first_error(serializer.errors)
        raise BusinessException(first_msg, code=ErrorCode.PARAM_ERROR)

    apartment_id = serializer.validated_data['apartment_id']
    user = request.user

    # 校验公寓是否存在且已上架
    try:
        apartment = Apartment.objects.get(id=apartment_id, status='published')
    except Apartment.DoesNotExist:
        raise NotFoundException('房源不存在或未上架')

    # 查找当前用户的收藏记录（包含已逻辑删除的）
    existing = Favorite.all_objects.filter(user=user, apartment=apartment).first()

    if existing and existing.deleted_at is None:
        # 已收藏 → 取消收藏（逻辑删除）
        existing.deleted_at = timezone.now()
        existing.save(update_fields=['deleted_at', 'updated_at'])
        logger.info(f'[Unfavorite] user={user.id}, apartment={apartment_id}')
        return unified_response(data={
            'is_favorited': False,
            'favorite_id': existing.id,
        })
    elif existing and existing.deleted_at is not None:
        # 已逻辑删除 → 恢复收藏
        existing.deleted_at = None
        existing.save(update_fields=['deleted_at', 'updated_at'])
        logger.info(f'[ReFavorite] user={user.id}, apartment={apartment_id}')
        return unified_response(data={
            'is_favorited': True,
            'favorite_id': existing.id,
        })
    else:
        # 未收藏 → 创建收藏
        favorite = Favorite.objects.create(user=user, apartment=apartment)
        logger.info(f'[Favorite] user={user.id}, apartment={apartment_id}')
        return unified_response(data={
            'is_favorited': True,
            'favorite_id': favorite.id,
        })


@extend_schema(
    request=None,
    responses={200: FavoriteListItemSerializer(many=True)},
    summary='我的收藏列表',
    description='返回当前登录用户的收藏列表，按收藏时间（created_at）倒序，支持分页。仅包含已上架房源。',
    tags=['收藏'],
    parameters=[
        {'name': 'page', 'in': 'query', 'schema': {'type': 'integer'}, 'description': '页码，默认 1'},
        {'name': 'page_size', 'in': 'query', 'schema': {'type': 'integer'}, 'description': '每页条数，默认 10，最大 100'},
    ],
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_favorites(request):
    """
    GET /api/v1/favorites
    我的收藏列表（按收藏时间倒序）
    """
    user = request.user

    # 查询当前用户有效收藏，关联公寓，预加载 district / street 避免 N+1
    queryset = Favorite.objects.filter(user=user).select_related(
        'apartment', 'apartment__district', 'apartment__street'
    ).order_by('-created_at', '-id')

    # 分页
    paginator = StandardPagination()
    page = paginator.paginate_queryset(queryset, request)

    # 手动构建响应数据（避免嵌套序列化器复杂度）
    items = []
    for fav in page:
        apt = fav.apartment
        items.append({
            'id': fav.id,
            'apartment_id': apt.id,
            'apartment_name': apt.name,
            'cover_image': apt.cover_image,
            'district_name': apt.district.name if apt.district else None,
            'street_name': apt.street.name if apt.street else None,
            'min_monthly_rent': apt.min_monthly_rent,
            'created_at': fav.created_at,
        })

    return paginator.get_paginated_response(items)


def _extract_first_error(errors):
    """从 serializer.errors 中提取第一个错误信息字符串"""
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

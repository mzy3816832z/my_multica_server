"""
字典视图
"""
import logging
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from drf_spectacular.utils import extend_schema

from core.response import unified_response
from core.exceptions import ParamErrorException
from apps.dicts.models import SystemDict
from apps.dicts.serializers import SystemDictSerializer

logger = logging.getLogger('apps')


@extend_schema(
    request=None,
    responses={200: SystemDictSerializer(many=True)},
    summary='字典列表',
    description='按 category 查询系统字典项列表。',
    tags=['字典'],
    parameters=[
        {
            'name': 'category',
            'in': 'query',
            'schema': {'type': 'string'},
            'description': '字典分类，如 layout_type、lease_term、facility、payment_method、window_type、window_orientation',
            'required': True,
        },
    ],
)
@api_view(['GET'])
@permission_classes([AllowAny])
def dict_list(request):
    """
    GET /api/v1/dicts?category=xxx
    """
    category = request.query_params.get('category')

    if not category:
        raise ParamErrorException('category 参数必填')

    queryset = SystemDict.objects.filter(
        category=category,
        is_active=True,
        deleted_at__isnull=True,
    ).order_by('sort', 'id')

    serializer = SystemDictSerializer(queryset, many=True)
    return unified_response(data=serializer.data)

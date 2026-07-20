"""
行政区划模块：视图
"""
import logging
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from drf_spectacular.utils import extend_schema

from core.response import unified_response, ErrorCode
from core.exceptions import ParamErrorException
from apps.districts.models import District
from apps.districts.serializers import DistrictListSerializer

logger = logging.getLogger('apps')


@extend_schema(
    request=None,
    responses={200: DistrictListSerializer(many=True)},
    summary='行政区划列表',
    description='获取行政区划列表。支持按层级(level)筛选，或按父级ID(parent_id)获取下级区划。',
    tags=['行政区划'],
    parameters=[
        {'name': 'level', 'in': 'query', 'schema': {'type': 'integer'}, 'description': '层级：1=行政区，2=街道/镇'},
        {'name': 'parent_id', 'in': 'query', 'schema': {'type': 'integer'}, 'description': '父级区划ID，获取下级区划'},
    ],
)
@api_view(['GET'])
@permission_classes([AllowAny])
def district_list(request):
    """
    GET /api/v1/districts
    获取行政区划列表
    """
    queryset = District.objects.all().order_by('sort', 'id')

    level = request.query_params.get('level')
    if level is not None:
        try:
            level_int = int(level)
            if level_int not in (1, 2):
                raise ParamErrorException('level 参数只能为 1（行政区）或 2（街道/镇）')
            queryset = queryset.filter(level=level_int)
        except ValueError:
            raise ParamErrorException('level 参数必须为整数')

    parent_id = request.query_params.get('parent_id')
    if parent_id is not None:
        try:
            parent_id_int = int(parent_id)
            queryset = queryset.filter(parent_id=parent_id_int)
        except ValueError:
            raise ParamErrorException('parent_id 参数必须为整数')

    serializer = DistrictListSerializer(queryset, many=True)
    return unified_response(data=serializer.data)

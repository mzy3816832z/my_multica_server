"""
行政区划视图
"""
import logging
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from drf_spectacular.utils import extend_schema

from core.response import unified_response
from core.exceptions import ParamErrorException
from apps.districts.models import District
from apps.districts.serializers import DistrictSerializer

logger = logging.getLogger('apps')


@extend_schema(
    request=None,
    responses={200: DistrictSerializer(many=True)},
    summary='行政区划列表',
    description='获取行政区划列表。level=1 返回上海行政区列表；level=2 需配合 parent_id 返回对应街道/镇列表。',
    tags=['行政区划'],
    parameters=[
        {'name': 'level', 'in': 'query', 'schema': {'type': 'integer'}, 'description': '层级：1=行政区，2=街道/镇', 'required': True},
        {'name': 'parent_id', 'in': 'query', 'schema': {'type': 'integer'}, 'description': '父级区划 ID，level=2 时必填'},
    ],
)
@api_view(['GET'])
@permission_classes([AllowAny])
def district_list(request):
    """
    GET /api/v1/districts?level=1
    GET /api/v1/districts?level=2&parent_id=xxx
    """
    level_str = request.query_params.get('level')
    parent_id_str = request.query_params.get('parent_id')

    # 校验 level 参数
    if level_str is None:
        raise ParamErrorException('level 参数必填')

    try:
        level = int(level_str)
    except (ValueError, TypeError):
        raise ParamErrorException('level 参数必须是整数')

    if level not in (1, 2):
        raise ParamErrorException('level 参数只能是 1 或 2')

    # level=2 时必须传 parent_id
    if level == 2:
        if parent_id_str is None:
            raise ParamErrorException('level=2 时 parent_id 参数必填')
        try:
            parent_id = int(parent_id_str)
        except (ValueError, TypeError):
            raise ParamErrorException('parent_id 参数必须是整数')

        # 校验父级是否存在
        try:
            parent = District.objects.get(id=parent_id, level=1, deleted_at__isnull=True)
        except District.DoesNotExist:
            raise ParamErrorException('parent_id 对应的行政区不存在')

        queryset = District.objects.filter(
            parent=parent,
            level=2,
            deleted_at__isnull=True,
        ).order_by('sort', 'id')
    else:
        queryset = District.objects.filter(
            level=1,
            deleted_at__isnull=True,
        ).order_by('sort', 'id')

    serializer = DistrictSerializer(queryset, many=True)
    return unified_response(data=serializer.data)

"""
商家房源模块路由

直接为不同 HTTP 方法绑定独立 DRF 视图函数，
不再使用 dispatch 模式透传 request。
"""
from django.urls import path
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from apps.apartments import views
from apps.apartments.serializers import (
    ApartmentCreateSerializer,
    ApartmentResponseSerializer,
    ApartmentUpdateSerializer,
    MerchantApartmentDeleteResponseSerializer,
    MerchantApartmentDetailSerializer,
    MerchantApartmentListSerializer,
    MerchantApartmentUpdateResponseSerializer,
)
from core.permissions import IsLandlord


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
@extend_schema(
    request=ApartmentCreateSerializer,
    responses={200: ApartmentResponseSerializer},
    summary='商家发布房源',
    description='商家发布房源并提交首次审核。校验公寓基础信息、至少 1 组房型、房型图片 ≤5 张、租期租金方案 ≥1 组；保存公寓状态为 pending_first_review 并创建 first_review 审核记录。',
    tags=['商家房源'],
    methods=['POST'],
)
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated, IsLandlord])
def merchant_apartments(request):
    """
    GET  /api/v1/merchant/apartments/   -> 商家已上架房源列表
    POST /api/v1/merchant/apartments/   -> 发布房源
    """
    if request.method == 'POST':
        return views.create_apartment(request)
    return views.merchant_apartment_list(request)


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
    methods=['PUT'],
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
    methods=['DELETE'],
)
@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated, IsLandlord])
def merchant_apartment_detail(request, id):
    """
    GET    /api/v1/merchant/apartments/<id>  -> 详情
    PUT    /api/v1/merchant/apartments/<id>  -> 更新
    DELETE /api/v1/merchant/apartments/<id>  -> 删除
    """
    if request.method == 'GET':
        return views.merchant_apartment_detail(request, id)
    elif request.method == 'PUT':
        return views.merchant_apartment_update(request, id)
    return views.merchant_apartment_delete(request, id)


urlpatterns = [
    path('', merchant_apartments, name='merchant-apartments'),
    path('<int:id>/', merchant_apartment_detail, name='merchant-apartment-detail'),
]

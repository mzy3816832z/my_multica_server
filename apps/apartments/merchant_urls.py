"""
商家房源模块路由

Django URL 路由按 URL 模式匹配，同一模式的不同 HTTP 方法需通过内部派发实现。
本文件直接为不同 HTTP 方法绑定独立视图函数，dispatch 作为纯 Python 函数
透传 Django HttpRequest 给各子视图，由各视图自身的 @api_view 完成 DRF 封装。
"""
from django.urls import path
from apps.apartments import views


def merchant_apartments(request):
    """
    POST /api/v1/merchant/apartments/   -> 发布房源
    GET  /api/v1/merchant/apartments/   -> 商家已上架房源列表
    """
    if request.method == 'POST':
        return views.create_apartment(request)
    return views.merchant_apartment_list(request)


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
    path('<int:id>', merchant_apartment_detail, name='merchant-apartment-detail'),
]

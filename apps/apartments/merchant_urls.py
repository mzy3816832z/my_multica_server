"""
商家房源模块路由
"""
from django.urls import path
from apps.apartments import views

urlpatterns = [
    # POST /api/v1/merchant/apartments/  -> 发布房源
    # GET  /api/v1/merchant/apartments/  -> 商家已上架房源列表
    path('', views.merchant_apartments_dispatch, name='merchant-apartments'),

    # GET    /api/v1/merchant/apartments/<id>  -> 详情
    # PUT    /api/v1/merchant/apartments/<id>  -> 更新
    # DELETE /api/v1/merchant/apartments/<id>  -> 删除
    path('<int:id>', views.merchant_apartment_detail_dispatch, name='merchant-apartment-detail'),
]

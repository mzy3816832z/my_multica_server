"""
商家房源模块路由
"""
from django.urls import path
from apps.apartments import views

urlpatterns = [
    path('apartments/', views.create_apartment, name='create-apartment'),
    path('apartments/list/', views.merchant_apartment_list, name='merchant-apartment-list'),
    path('apartments/<int:id>/', views.merchant_apartment_detail, name='merchant-apartment-detail'),
    path('apartments/<int:id>/update/', views.merchant_apartment_update, name='merchant-apartment-update'),
    path('apartments/<int:id>/delete/', views.merchant_apartment_delete, name='merchant-apartment-delete'),
]

"""
房源模块路由
"""
from django.urls import path
from apps.apartments import views

urlpatterns = [
    # 公共房源接口（公开访问）
    path('', views.apartment_list, name='apartment-list'),
    path('<int:id>/', views.apartment_detail, name='apartment-detail'),
    path('<int:id>/room-types/', views.apartment_room_types, name='apartment-room-types'),
    path('room-types/<int:id>/', views.room_type_detail, name='room-type-detail'),
]

"""
行政区划模块路由
"""
from django.urls import path
from apps.districts import views

urlpatterns = [
    path('', views.district_list, name='district-list'),
]

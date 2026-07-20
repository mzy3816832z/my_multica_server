"""
行政区划路由
"""
from django.urls import path
from apps.districts.views import district_list

urlpatterns = [
    path('', district_list, name='district-list'),
]

"""
房源模块路由
"""
from django.urls import path
from apps.apartments import views

urlpatterns = [
    path('', views.create_apartment, name='create-apartment'),
]

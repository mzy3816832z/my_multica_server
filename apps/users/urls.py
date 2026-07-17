"""
用户模块路由
"""
from django.urls import path
from apps.users import views

urlpatterns = [
    path('sms-code', views.send_sms_code, name='send-sms-code'),
]

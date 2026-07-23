"""
用户模块路由
"""
from django.urls import path
from apps.users import views

urlpatterns = [
    path('sms-code', views.send_sms_code, name='send-sms-code'),
    path('register', views.register, name='register'),
    path('login-by-password', views.login_by_password, name='login-by-password'),
    path('login-by-code', views.login_by_code, name='login-by-code'),
    path('select-role', views.select_role, name='select-role'),
    path('reset-password', views.reset_password, name='reset-password'),
    path('change-password', views.change_password, name='change-password'),
    path('me', views.me, name='me'),
]

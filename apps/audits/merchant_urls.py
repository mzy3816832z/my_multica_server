"""
商家审核模块路由
"""
from django.urls import path
from apps.audits import views

urlpatterns = [
    path('audits/', views.merchant_audit_list, name='merchant-audit-list'),
]

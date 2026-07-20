"""
管理员审核模块路由
"""
from django.urls import path
from apps.audits import views

urlpatterns = [
    path('audits/', views.audit_list, name='admin-audit-list'),
    path('audits/<int:id>/', views.audit_detail, name='admin-audit-detail'),
    path('audits/<int:id>/approve/', views.audit_approve, name='admin-audit-approve'),
    path('audits/<int:id>/reject/', views.audit_reject, name='admin-audit-reject'),
]

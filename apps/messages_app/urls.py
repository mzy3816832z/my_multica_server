"""
消息模块路由
"""
from django.urls import path
from apps.messages_app import views

urlpatterns = [
    path('', views.message_list, name='message-list'),
    path('<int:id>/read/', views.message_read, name='message-read'),
    path('unread-count/', views.message_unread_count, name='message-unread-count'),
]

"""
收藏模块路由
"""
from django.urls import path
from apps.favorites import views

urlpatterns = [
    path('', views.toggle_favorite, name='favorite-toggle'),
    path('my/', views.my_favorites, name='my-favorites'),
]

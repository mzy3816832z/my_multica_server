"""
收藏模块路由
"""
from django.urls import path
from apps.favorites import views

urlpatterns = [
    path('', views.add_favorite, name='favorite-add'),
    path('my/', views.my_favorites, name='my-favorites'),
    path('<int:pk>/', views.delete_favorite, name='favorite-delete'),
]

"""
收藏模块路由
"""
from django.urls import path
from apps.favorites import views

urlpatterns = [
    path('', views.add_favorite, name='favorite-add'),
    path('my/', views.my_favorites, name='my-favorites'),
    path('by-apartment/<int:apartment_id>/', views.delete_favorite_by_apartment, name='favorite-delete-by-apartment'),
]

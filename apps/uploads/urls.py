"""
上传模块路由
"""
from django.urls import path
from apps.uploads import views

urlpatterns = [
    path('image', views.upload_image, name='upload-image'),
]

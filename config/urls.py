"""
URL configuration for config project.
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from core.views import health_check


urlpatterns = [
    path('admin/', admin.site.urls),
    path('health', health_check, name='health'),
    path('api/v1/auth/', include('apps.users.urls')),
    path('api/v1/uploads/', include('apps.uploads.urls')),
    path('api/v1/apartments/', include('apps.apartments.urls')),
    path('api/v1/favorites/', include('apps.favorites.urls')),
    path('api/v1/merchant/apartments/', include('apps.apartments.merchant_urls')),
    path('api/v1/merchant/audits/', include('apps.audits.merchant_urls')),
    path('api/v1/messages/', include('apps.messages_app.urls')),
    path('api/v1/admin/', include('apps.audits.urls')),
    path('api/v1/districts/', include('apps.districts.urls')),
    path('api/v1/dicts/', include('apps.dicts.urls')),

    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]
# 静态文件服务：生产环境通过 Nginx 代理，开发环境由 Django 提供
# 无论 DEBUG 模式如何，都注册 /uploads/ 路由，确保图片可访问
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

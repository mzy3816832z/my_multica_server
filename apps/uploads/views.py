"""
图片上传视图
"""
import os
import uuid
from datetime import datetime
from PIL import Image
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework import serializers
from drf_spectacular.utils import extend_schema

from core.response import unified_response, ErrorCode
from core.exceptions import ParamErrorException


# 允许的图片格式（MIME 类型映射）
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp'}
ALLOWED_CONTENT_TYPES = {
    'image/jpeg',
    'image/png',
    'image/webp',
}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB


class ImageUploadSerializer(serializers.Serializer):
    """图片上传请求序列化器"""
    file = serializers.ImageField(
        help_text='图片文件，限制 5MB，仅允许 jpg/png/webp',
    )


class ImageUploadResponseSerializer(serializers.Serializer):
    """图片上传响应序列化器"""
    url = serializers.URLField(help_text='图片可访问 URL')
    path = serializers.CharField(help_text='图片相对存储路径')


def _validate_image(file_obj):
    """
    校验图片文件：大小、格式
    返回 (is_valid, error_message)
    """
    # 校验文件大小
    if file_obj.size > MAX_FILE_SIZE:
        return False, f'图片大小超过限制，最大允许 5MB，当前 {file_obj.size / 1024 / 1024:.2f}MB'

    # 校验文件扩展名
    name = getattr(file_obj, 'name', '')
    ext = os.path.splitext(name)[1].lower().lstrip('.')
    if ext == 'jpg':
        ext = 'jpeg'
    if ext not in ALLOWED_EXTENSIONS:
        return False, f'不支持的图片格式：{ext}，仅允许 jpg、png、webp'

    # 校验内容类型
    content_type = getattr(file_obj, 'content_type', '')
    if content_type and content_type not in ALLOWED_CONTENT_TYPES:
        return False, f'不支持的图片类型：{content_type}'

    # 尝试用 Pillow 打开验证图片完整性
    try:
        file_obj.seek(0)
        img = Image.open(file_obj)
        img.verify()  # 验证图片文件完整性
        file_obj.seek(0)
    except Exception:
        return False, '图片文件损坏或格式不正确'

    return True, None


def _generate_storage_path(filename):
    """
    生成存储路径：uploads/images/YYYY/MM/DD/uuid.ext
    """
    now = datetime.now()
    ext = os.path.splitext(filename)[1].lower()
    if ext == '.jpg':
        ext = '.jpeg'
    unique_name = f"{uuid.uuid4().hex}{ext}"
    relative_path = os.path.join(
        'images',
        now.strftime('%Y'),
        now.strftime('%m'),
        now.strftime('%d'),
        unique_name,
    )
    return relative_path


def _save_uploaded_file(file_obj, relative_path):
    """
    保存上传文件到 MEDIA_ROOT
    """
    absolute_path = os.path.join(settings.MEDIA_ROOT, relative_path)
    os.makedirs(os.path.dirname(absolute_path), exist_ok=True)

    with open(absolute_path, 'wb+') as destination:
        for chunk in file_obj.chunks():
            destination.write(chunk)

    return absolute_path


@extend_schema(
    request=ImageUploadSerializer,
    responses={200: ImageUploadResponseSerializer},
    summary='单张图片上传',
    description='上传单张图片，限制 5MB，仅允许 jpg/png/webp 格式。返回可访问 URL。',
    tags=['上传'],
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_image(request):
    """
    POST /api/v1/uploads/image
    单张图片上传
    """
    file_obj = request.FILES.get('file')
    if not file_obj:
        raise ParamErrorException('请上传图片文件（file 字段）')

    # 校验图片
    is_valid, error_msg = _validate_image(file_obj)
    if not is_valid:
        raise ParamErrorException(error_msg)

    # 生成存储路径并保存
    relative_path = _generate_storage_path(file_obj.name)
    _save_uploaded_file(file_obj, relative_path)

    # 构建可访问 URL
    url = f"{settings.MEDIA_URL}{relative_path.replace(os.sep, '/')}"

    return unified_response(
        data={
            'url': url,
            'path': relative_path,
        },
        code=ErrorCode.SUCCESS,
    )

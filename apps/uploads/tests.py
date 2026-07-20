"""
图片上传模块单元测试
"""
import os
import io
import tempfile
from PIL import Image

from django.test import TestCase, override_settings
from django.conf import settings
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.users.models import User


# 使用临时目录作为 MEDIA_ROOT，避免污染项目目录
TEMP_MEDIA_ROOT = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT, ALLOWED_HOSTS=['*', 'testserver'])
class UploadImageTests(TestCase):
    """图片上传接口测试"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create(
            phone='13800138000',
            hashed_password='fake_hash',
            role='tenant',
            is_active=True,
        )
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')

    def tearDown(self):
        # 清理临时上传文件
        import shutil
        if os.path.exists(TEMP_MEDIA_ROOT):
            shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def _create_image_file(self, ext='png', size=(100, 100), color=(255, 0, 0)):
        """创建测试图片文件，返回 InMemoryUploadedFile"""
        img = Image.new('RGB', size, color)
        buffer = io.BytesIO()
        mime = 'image/png'
        if ext == 'jpg' or ext == 'jpeg':
            img.save(buffer, format='JPEG')
            mime = 'image/jpeg'
        elif ext == 'webp':
            img.save(buffer, format='WEBP')
            mime = 'image/webp'
        else:
            img.save(buffer, format='PNG')
        buffer.seek(0)
        from django.core.files.uploadedfile import InMemoryUploadedFile
        return InMemoryUploadedFile(
            buffer, 'file', f'test.{ext}', mime,
            buffer.getbuffer().nbytes, None
        )

    def test_upload_image_success_png(self):
        """成功上传 PNG 图片"""
        image = self._create_image_file('png')
        response = self.client.post(
            '/api/v1/uploads/image',
            {'file': image},
            format='multipart',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['code'], 0)
        self.assertIn('url', response.data['data'])
        self.assertIn('path', response.data['data'])
        # 验证文件实际存在
        relative_path = response.data['data']['path']
        absolute_path = os.path.join(TEMP_MEDIA_ROOT, relative_path)
        self.assertTrue(os.path.exists(absolute_path))

    def test_upload_image_success_jpg(self):
        """成功上传 JPG 图片"""
        image = self._create_image_file('jpg')
        response = self.client.post(
            '/api/v1/uploads/image',
            {'file': image},
            format='multipart',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['code'], 0)
        self.assertIn('url', response.data['data'])

    def test_upload_image_success_webp(self):
        """成功上传 WEBP 图片"""
        image = self._create_image_file('webp')
        response = self.client.post(
            '/api/v1/uploads/image',
            {'file': image},
            format='multipart',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['code'], 0)
        self.assertIn('url', response.data['data'])

    def test_upload_image_without_auth(self):
        """未登录上传应返回 401"""
        client = APIClient()
        image = self._create_image_file('png')
        response = client.post(
            '/api/v1/uploads/image',
            {'file': image},
            format='multipart',
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data['code'], 401001)

    def test_upload_image_no_file(self):
        """未提供文件应返回 400001"""
        response = self.client.post(
            '/api/v1/uploads/image',
            {},
            format='multipart',
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['code'], 400001)

    def test_upload_image_oversize(self):
        """上传超过 5MB 的图片应返回 400001"""
        # 创建一个较大的图片（超过 5MB）
        img = Image.new('RGB', (4000, 4000), (255, 0, 0))
        buffer = io.BytesIO()
        img.save(buffer, format='BMP')  # BMP 无压缩，容易超过 5MB
        buffer.seek(0)
        from django.core.files.uploadedfile import InMemoryUploadedFile
        file_obj = InMemoryUploadedFile(
            buffer, 'file', 'test.bmp', 'image/bmp',
            buffer.getbuffer().nbytes, None
        )

        response = self.client.post(
            '/api/v1/uploads/image',
            {'file': file_obj},
            format='multipart',
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['code'], 400001)

    def test_upload_image_invalid_format(self):
        """上传非法格式（如 GIF）应返回 400001"""
        img = Image.new('RGB', (100, 100), (255, 0, 0))
        buffer = io.BytesIO()
        img.save(buffer, format='GIF')
        buffer.seek(0)
        from django.core.files.uploadedfile import InMemoryUploadedFile
        file_obj = InMemoryUploadedFile(
            buffer, 'file', 'test.gif', 'image/gif',
            buffer.getbuffer().nbytes, None
        )
        response = self.client.post(
            '/api/v1/uploads/image',
            {'file': file_obj},
            format='multipart',
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['code'], 400001)

    def test_upload_image_corrupted(self):
        """上传损坏的图片应返回 400001"""
        buffer = io.BytesIO(b'not an image at all')
        from django.core.files.uploadedfile import InMemoryUploadedFile
        file_obj = InMemoryUploadedFile(
            buffer, 'file', 'test.png', 'image/png',
            buffer.getbuffer().nbytes, None
        )
        response = self.client.post(
            '/api/v1/uploads/image',
            {'file': file_obj},
            format='multipart',
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['code'], 400001)

    def test_upload_image_url_accessible(self):
        """上传后图片 URL 可访问（验证文件存在且 URL 可解析）"""
        image = self._create_image_file('png')
        response = self.client.post(
            '/api/v1/uploads/image',
            {'file': image},
            format='multipart',
        )
        self.assertEqual(response.status_code, 200)
        url = response.data['data']['url']
        url = url.replace('\\', '/')
        path = response.data['data']['path']

        # 验证文件实际存在
        absolute_path = os.path.join(TEMP_MEDIA_ROOT, path)
        self.assertTrue(os.path.exists(absolute_path))

        # 验证 URL 格式正确（以 MEDIA_URL 开头）
        self.assertTrue(url.startswith(settings.MEDIA_URL))

        # 验证 URL 路径拼接后指向真实文件（去掉 MEDIA_URL 前缀）
        relative_url = url[len(settings.MEDIA_URL):]
        full_path = os.path.join(TEMP_MEDIA_ROOT, relative_url)
        self.assertTrue(os.path.exists(full_path))

    def test_upload_image_path_structure(self):
        """上传路径按日期分目录存储"""
        image = self._create_image_file('png')
        response = self.client.post(
            '/api/v1/uploads/image',
            {'file': image},
            format='multipart',
        )
        self.assertEqual(response.status_code, 200)
        path = response.data['data']['path']
        # 路径格式：images/YYYY/MM/DD/uuid.png（统一使用正斜杠）
        path = path.replace('\\', '/')
        parts = path.split('/')
        self.assertEqual(parts[0], 'images')
        self.assertEqual(len(parts), 5)  # images/YYYY/MM/DD/filename
        self.assertTrue(parts[4].endswith('.png'))

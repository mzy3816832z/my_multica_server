"""
收藏模块单元测试
"""
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.users.models import User
from apps.districts.models import District
from apps.apartments.models import Apartment, RoomType, RentalPlan
from apps.favorites.models import Favorite


class FavoriteAddTests(TestCase):
    """添加收藏接口测试"""

    def setUp(self):
        self.client = APIClient()

        # 创建行政区与街道
        self.district = District.objects.create(name='浦东新区', level=1, code='310115', sort=0)
        self.street = District.objects.create(name='陆家嘴街道', level=2, code='310115001', parent=self.district, sort=0)

        # 创建商家与租客
        self.landlord = User.objects.create(phone='13800138000', password="fake", role='landlord', is_active=True)
        self.tenant = User.objects.create(phone='13900139000', password="fake", role='tenant', is_active=True)
        self.tenant_token = self._get_token(self.tenant)

        # 创建已上架房源
        self.apartment = Apartment.objects.create(
            landlord=self.landlord,
            name='测试公寓',
            cover_image='https://example.com/cover.jpg',
            description='测试描述',
            district=self.district,
            street=self.street,
            detail_address='测试路1号',
            contact_phone='13800138000',
            status='published',
            min_monthly_rent=3000,
        )
        self.room = RoomType.objects.create(
            apartment=self.apartment,
            name='标准单间',
            images=['https://example.com/room.jpg'],
            facilities=['air_conditioner'],
            layout_type='studio',
            window_type='external',
            orientation='south',
            floor=5,
            sort=0,
        )
        RentalPlan.objects.create(room_type=self.room, lease_term='1_month', monthly_rent=3000, payment_method='pay_1_deposit_1')

        # 创建未上架房源
        self.unpublished = Apartment.objects.create(
            landlord=self.landlord,
            name='未上架房源',
            cover_image='https://example.com/up.jpg',
            description='未上架',
            district=self.district,
            street=self.street,
            detail_address='测试路2号',
            contact_phone='13800138001',
            status='pending_first_review',
            min_monthly_rent=2000,
        )

        self.url = '/api/v1/favorites/'

    def _get_token(self, user):
        refresh = RefreshToken.for_user(user)
        refresh['role'] = user.role
        refresh['phone'] = user.phone
        refresh['username'] = user.username
        return str(refresh.access_token)

    def test_favorite_success(self):
        """首次收藏成功"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.tenant_token}')
        response = self.client.post(self.url, {'apartment_id': self.apartment.id})
        self.assertEqual(response.status_code, 200)
        data = response.json()['data']
        self.assertIsNotNone(data['id'])
        self.assertEqual(data['apartment_id'], self.apartment.id)
        # 数据库验证
        self.assertTrue(Favorite.objects.filter(user=self.tenant, apartment=self.apartment).exists())

    def test_favorite_already_favorited(self):
        """重复收藏同一公寓 → 返回已有记录"""
        fav = Favorite.objects.create(user=self.tenant, apartment=self.apartment)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.tenant_token}')
        response = self.client.post(self.url, {'apartment_id': self.apartment.id})
        self.assertEqual(response.status_code, 200)
        data = response.json()['data']
        self.assertEqual(data['id'], fav.id)
        self.assertEqual(data['apartment_id'], self.apartment.id)
        # 数据库验证仍然有效
        self.assertTrue(Favorite.objects.filter(user=self.tenant, apartment=self.apartment).exists())

    def test_favorite_re_favorite(self):
        """取消收藏后再次收藏 → 恢复记录"""
        fav = Favorite.objects.create(user=self.tenant, apartment=self.apartment)
        fav.deleted_at = __import__('django.utils.timezone').utils.timezone.now()
        fav.save(update_fields=['deleted_at'])

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.tenant_token}')
        response = self.client.post(self.url, {'apartment_id': self.apartment.id})
        self.assertEqual(response.status_code, 200)
        data = response.json()['data']
        # 验证恢复的是同一条记录
        self.assertEqual(data['id'], fav.id)
        fav.refresh_from_db()
        self.assertIsNone(fav.deleted_at)

    def test_favorite_unpublished_apartment(self):
        """收藏未上架房源返回 404"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.tenant_token}')
        response = self.client.post(self.url, {'apartment_id': self.unpublished.id})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['code'], 404001)

    def test_favorite_nonexistent_apartment(self):
        """收藏不存在的房源返回 404"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.tenant_token}')
        response = self.client.post(self.url, {'apartment_id': 99999})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['code'], 404001)

    def test_favorite_invalid_param(self):
        """非法参数返回 400"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.tenant_token}')
        response = self.client.post(self.url, {'apartment_id': 'abc'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['code'], 400001)

    def test_favorite_unauthorized(self):
        """未登录返回 401"""
        response = self.client.post(self.url, {'apartment_id': self.apartment.id})
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()['code'], 401001)


class MyFavoritesListTests(TestCase):
    """我的收藏列表接口测试"""

    def setUp(self):
        self.client = APIClient()

        self.district = District.objects.create(name='浦东新区', level=1, code='310115', sort=0)
        self.street = District.objects.create(name='陆家嘴街道', level=2, code='310115001', parent=self.district, sort=0)
        self.district2 = District.objects.create(name='黄浦区', level=1, code='310101', sort=0)
        self.street2 = District.objects.create(name='南京东路街道', level=2, code='310101001', parent=self.district2, sort=0)

        self.landlord = User.objects.create(phone='13800138000', password="fake", role='landlord', is_active=True)
        self.tenant = User.objects.create(phone='13900139000', password="fake", role='tenant', is_active=True)
        self.tenant_token = self._get_token(self.tenant)

        # 公寓 A
        self.apartment_a = Apartment.objects.create(
            landlord=self.landlord,
            name='公寓A',
            cover_image='https://example.com/a.jpg',
            description='描述A',
            district=self.district,
            street=self.street,
            detail_address='测试路1号',
            contact_phone='13800138000',
            status='published',
            min_monthly_rent=3000,
        )
        # 公寓 B
        self.apartment_b = Apartment.objects.create(
            landlord=self.landlord,
            name='公寓B',
            cover_image='https://example.com/b.jpg',
            description='描述B',
            district=self.district2,
            street=self.street2,
            detail_address='测试路2号',
            contact_phone='13800138001',
            status='published',
            min_monthly_rent=5000,
        )
        # 公寓 C（未上架）
        self.apartment_c = Apartment.objects.create(
            landlord=self.landlord,
            name='公寓C',
            cover_image='https://example.com/c.jpg',
            description='描述C',
            district=self.district,
            street=self.street,
            detail_address='测试路3号',
            contact_phone='13800138002',
            status='pending_first_review',
            min_monthly_rent=2000,
        )

        self.url = '/api/v1/favorites/my/'

    def _get_token(self, user):
        refresh = RefreshToken.for_user(user)
        refresh['role'] = user.role
        refresh['phone'] = user.phone
        refresh['username'] = user.username
        return str(refresh.access_token)

    def test_list_empty(self):
        """无收藏时返回空列表"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.tenant_token}')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        data = response.json()['data']
        self.assertEqual(data['total'], 0)
        self.assertEqual(len(data['items']), 0)

    def test_list_ordered_by_created_at_desc(self):
        """列表按收藏时间倒序"""
        Favorite.objects.create(user=self.tenant, apartment=self.apartment_a)
        Favorite.objects.create(user=self.tenant, apartment=self.apartment_b)

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.tenant_token}')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        data = response.json()['data']
        self.assertEqual(data['total'], 2)
        items = data['items']
        # 后收藏的 B 排在前面
        self.assertEqual(items[0]['apartment_id'], self.apartment_b.id)
        self.assertEqual(items[1]['apartment_id'], self.apartment_a.id)

    def test_list_excludes_deleted(self):
        """取消收藏的房源不在列表中"""
        fav = Favorite.objects.create(user=self.tenant, apartment=self.apartment_a)
        Favorite.objects.create(user=self.tenant, apartment=self.apartment_b)
        # 取消收藏 A
        fav.deleted_at = __import__('django.utils.timezone').utils.timezone.now()
        fav.save(update_fields=['deleted_at'])

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.tenant_token}')
        response = self.client.get(self.url)
        data = response.json()['data']
        self.assertEqual(data['total'], 1)
        self.assertEqual(data['items'][0]['apartment_id'], self.apartment_b.id)

    def test_list_fields(self):
        """列表字段完整"""
        Favorite.objects.create(user=self.tenant, apartment=self.apartment_a)

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.tenant_token}')
        response = self.client.get(self.url)
        data = response.json()['data']
        item = data['items'][0]
        self.assertIn('id', item)
        self.assertIn('apartment_id', item)
        self.assertIn('apartment_name', item)
        self.assertIn('cover_image', item)
        self.assertIn('district_name', item)
        self.assertIn('street_name', item)
        self.assertIn('min_monthly_rent', item)
        self.assertIn('created_at', item)
        self.assertEqual(item['apartment_name'], '公寓A')
        self.assertEqual(item['district_name'], '浦东新区')
        self.assertEqual(item['street_name'], '陆家嘴街道')
        self.assertEqual(item['min_monthly_rent'], 3000)

    def test_list_pagination(self):
        """分页生效"""
        Favorite.objects.create(user=self.tenant, apartment=self.apartment_a)
        Favorite.objects.create(user=self.tenant, apartment=self.apartment_b)

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.tenant_token}')
        response = self.client.get(self.url, {'page': 1, 'page_size': 1})
        data = response.json()['data']
        self.assertEqual(len(data['items']), 1)
        self.assertEqual(data['total'], 2)
        self.assertEqual(data['page'], 1)
        self.assertEqual(data['page_size'], 1)

    def test_list_unauthorized(self):
        """未登录返回 401"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()['code'], 401001)


class FavoriteDeleteTests(TestCase):
    """取消收藏接口测试"""

    def setUp(self):
        self.client = APIClient()

        self.district = District.objects.create(name='浦东新区', level=1, code='310115', sort=0)
        self.street = District.objects.create(name='陆家嘴街道', level=2, code='310115001', parent=self.district, sort=0)

        self.landlord = User.objects.create(phone='13800138000', password="fake", role='landlord', is_active=True)
        self.tenant = User.objects.create(phone='13900139000', password="fake", role='tenant', is_active=True)
        self.other_tenant = User.objects.create(phone='13700137000', password="fake", role='tenant', is_active=True)
        self.tenant_token = self._get_token(self.tenant)
        self.other_token = self._get_token(self.other_tenant)

        self.apartment = Apartment.objects.create(
            landlord=self.landlord,
            name='测试公寓',
            cover_image='https://example.com/cover.jpg',
            description='测试描述',
            district=self.district,
            street=self.street,
            detail_address='测试路1号',
            contact_phone='13800138000',
            status='published',
            min_monthly_rent=3000,
        )

        self.favorite = Favorite.objects.create(user=self.tenant, apartment=self.apartment)

    def _get_token(self, user):
        refresh = RefreshToken.for_user(user)
        refresh['role'] = user.role
        refresh['phone'] = user.phone
        refresh['username'] = user.username
        return str(refresh.access_token)

    def test_delete_success(self):
        """正常取消收藏"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.tenant_token}')
        response = self.client.delete(f'/api/v1/favorites/{self.favorite.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['code'], 0)
        # 验证逻辑删除
        self.assertFalse(Favorite.objects.filter(id=self.favorite.id).exists())
        self.assertTrue(Favorite.all_objects.filter(id=self.favorite.id, deleted_at__isnull=False).exists())

    def test_delete_not_found(self):
        """取消不存在的收藏记录"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.tenant_token}')
        response = self.client.delete('/api/v1/favorites/99999/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['code'], 404001)

    def test_delete_other_user_favorite(self):
        """不能取消别人的收藏"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.other_token}')
        response = self.client.delete(f'/api/v1/favorites/{self.favorite.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['code'], 404001)
        # 验证记录未被删除
        self.assertTrue(Favorite.objects.filter(id=self.favorite.id).exists())

    def test_delete_unauthorized(self):
        """未登录返回 401"""
        response = self.client.delete(f'/api/v1/favorites/{self.favorite.id}/')
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()['code'], 401001)

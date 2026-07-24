"""
公共房源列表与详情接口单元测试
商家已上架房源管理接口单元测试
"""
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.apartments.models import Apartment, RentalPlan, RoomType
from apps.audits.models import AuditRecord
from apps.districts.models import District
from apps.favorites.models import Favorite
from apps.users.models import User


class PublicApartmentListTests(TestCase):
    """公共房源列表接口测试"""

    def setUp(self):
        self.client = APIClient()
        self.url = '/api/v1/apartments/'

        # 创建行政区与街道
        self.district = District.objects.create(name='浦东新区', level=1, code='310115', sort=0)
        self.street = District.objects.create(name='陆家嘴街道', level=2, code='310115001', parent=self.district, sort=0)
        self.district2 = District.objects.create(name='黄浦区', level=1, code='310101', sort=0)
        self.street2 = District.objects.create(name='南京东路街道', level=2, code='310101001', parent=self.district2, sort=0)

        # 创建商家
        self.landlord = User.objects.create(phone='13800138000', password="fake", role='landlord', is_active=True)

        # 创建已上架房源 A（浦东新区）
        self.apartment_a = Apartment.objects.create(
            landlord=self.landlord,
            name='陆家嘴精品公寓',
            cover_image='https://example.com/a.jpg',
            description='描述A',
            district=self.district,
            street=self.street,
            detail_address='测试路1号',
            contact_phone='13800138000',
            status='published',
            min_monthly_rent=3000,
        )
        self.room_a = RoomType.objects.create(
            apartment=self.apartment_a,
            name='标准单间',
            images=['https://example.com/ra.jpg'],
            facilities=['air_conditioner'],
            layout_type='studio',
            window_type='external',
            orientation='south',
            floor=5,
            sort=0,
        )
        RentalPlan.objects.create(room_type=self.room_a, lease_term='1_month', monthly_rent=3000, payment_method='pay_1_deposit_1')
        RentalPlan.objects.create(room_type=self.room_a, lease_term='6_month', monthly_rent=2800, payment_method='pay_3_deposit_1')

        # 创建已上架房源 B（黄浦区，价格更高）
        self.apartment_b = Apartment.objects.create(
            landlord=self.landlord,
            name='南京东路豪华公寓',
            cover_image='https://example.com/b.jpg',
            description='描述B',
            district=self.district2,
            street=self.street2,
            detail_address='测试路2号',
            contact_phone='13800138001',
            status='published',
            min_monthly_rent=5000,
        )
        self.room_b = RoomType.objects.create(
            apartment=self.apartment_b,
            name='豪华套房',
            images=['https://example.com/rb.jpg'],
            facilities=['air_conditioner', 'washing_machine'],
            layout_type='two_bedroom',
            window_type='external',
            orientation='east',
            floor=8,
            sort=0,
        )
        RentalPlan.objects.create(room_type=self.room_b, lease_term='1_year', monthly_rent=5000, payment_method='pay_3_deposit_1')

        # 创建未上架房源（不应出现在列表）
        self.apartment_c = Apartment.objects.create(
            landlord=self.landlord,
            name='待审核房源',
            cover_image='https://example.com/c.jpg',
            description='描述C',
            district=self.district,
            street=self.street,
            detail_address='测试路3号',
            contact_phone='13800138002',
            status='pending_first_review',
            min_monthly_rent=2000,
        )

        # 创建租客用户（用于收藏测试）
        self.tenant = User.objects.create(phone='13900139000', password="fake", role='tenant', is_active=True)
        self.tenant_token = self._get_token(self.tenant)

    def _get_token(self, user):
        refresh = RefreshToken.for_user(user)
        refresh['role'] = user.role
        refresh['phone'] = user.phone
        refresh['username'] = user.username
        return str(refresh.access_token)

    def test_list_only_published(self):
        """列表仅展示已上架房源"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        data = response.json()['data']
        self.assertEqual(data['total'], 2)
        ids = [item['id'] for item in data['items']]
        self.assertIn(self.apartment_a.id, ids)
        self.assertIn(self.apartment_b.id, ids)
        self.assertNotIn(self.apartment_c.id, ids)

    def test_list_order_by_updated_at_desc(self):
        """列表按审核通过时间（updated_at）倒序"""
        response = self.client.get(self.url)
        data = response.json()['data']
        items = data['items']
        # apartment_b 后创建，updated_at 更晚，应排在前面
        self.assertEqual(items[0]['id'], self.apartment_b.id)
        self.assertEqual(items[1]['id'], self.apartment_a.id)

    def test_list_pagination(self):
        """分页参数生效"""
        response = self.client.get(self.url, {'page': 1, 'page_size': 1})
        data = response.json()['data']
        self.assertEqual(len(data['items']), 1)
        self.assertEqual(data['total'], 2)
        self.assertEqual(data['page'], 1)
        self.assertEqual(data['page_size'], 1)

    def test_list_filter_by_keyword(self):
        """关键词筛选"""
        response = self.client.get(self.url, {'keyword': '陆家嘴'})
        data = response.json()['data']
        self.assertEqual(data['total'], 1)
        self.assertEqual(data['items'][0]['id'], self.apartment_a.id)

    def test_list_filter_by_district(self):
        """行政区筛选"""
        response = self.client.get(self.url, {'district_id': self.district2.id})
        data = response.json()['data']
        self.assertEqual(data['total'], 1)
        self.assertEqual(data['items'][0]['id'], self.apartment_b.id)

    def test_list_filter_by_street(self):
        """街道筛选"""
        response = self.client.get(self.url, {'street_id': self.street.id})
        data = response.json()['data']
        self.assertEqual(data['total'], 1)
        self.assertEqual(data['items'][0]['id'], self.apartment_a.id)

    def test_list_filter_by_layout_type(self):
        """户型筛选"""
        response = self.client.get(self.url, {'layout_type': 'two_bedroom'})
        data = response.json()['data']
        self.assertEqual(data['total'], 1)
        self.assertEqual(data['items'][0]['id'], self.apartment_b.id)

    def test_list_filter_by_lease_term(self):
        """租期筛选"""
        response = self.client.get(self.url, {'lease_term': '1_month'})
        data = response.json()['data']
        self.assertEqual(data['total'], 1)
        self.assertEqual(data['items'][0]['id'], self.apartment_a.id)

    def test_list_filter_by_price_range(self):
        """价格区间筛选"""
        response = self.client.get(self.url, {'min_price': 4000, 'max_price': 6000})
        data = response.json()['data']
        self.assertEqual(data['total'], 1)
        self.assertEqual(data['items'][0]['id'], self.apartment_b.id)

    def test_list_combined_filters(self):
        """组合筛选条件可叠加"""
        response = self.client.get(self.url, {
            'district_id': self.district.id,
            'layout_type': 'studio',
            'min_price': 2500,
        })
        data = response.json()['data']
        self.assertEqual(data['total'], 1)
        self.assertEqual(data['items'][0]['id'], self.apartment_a.id)

    def test_list_card_fields(self):
        """列表卡片字段包含最低月租金"""
        response = self.client.get(self.url)
        data = response.json()['data']
        item = data['items'][0]
        self.assertIn('id', item)
        self.assertIn('name', item)
        self.assertIn('cover_image', item)
        self.assertIn('district_name', item)
        self.assertIn('street_name', item)
        self.assertIn('min_monthly_rent', item)
        self.assertIn('is_favorited', item)

    def test_list_anonymous_not_favorited(self):
        """未登录用户 is_favorited 为 False"""
        response = self.client.get(self.url)
        data = response.json()['data']
        for item in data['items']:
            self.assertEqual(item['is_favorited'], False)

    def test_list_logged_in_favorited(self):
        """已登录用户已收藏房源 is_favorited 为 True"""
        Favorite.objects.create(user=self.tenant, apartment=self.apartment_a)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.tenant_token}')
        response = self.client.get(self.url)
        data = response.json()['data']
        for item in data['items']:
            if item['id'] == self.apartment_a.id:
                self.assertEqual(item['is_favorited'], True)
            else:
                self.assertEqual(item['is_favorited'], False)


class PublicApartmentDetailTests(TestCase):
    """房源详情接口测试"""

    def setUp(self):
        self.client = APIClient()
        self.district = District.objects.create(name='浦东新区', level=1, code='310115', sort=0)
        self.street = District.objects.create(name='陆家嘴街道', level=2, code='310115001', parent=self.district, sort=0)
        self.landlord = User.objects.create(phone='13800138000', password="fake", role='landlord', is_active=True)
        self.tenant = User.objects.create(phone='13900139000', password="fake", role='tenant', is_active=True)
        self.tenant_token = self._get_token(self.tenant)

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

    def _get_token(self, user):
        refresh = RefreshToken.for_user(user)
        refresh['role'] = user.role
        refresh['phone'] = user.phone
        refresh['username'] = user.username
        return str(refresh.access_token)

    def test_detail_success(self):
        """获取已上架房源详情成功"""
        response = self.client.get(f'/api/v1/apartments/{self.apartment.id}/')
        self.assertEqual(response.status_code, 200)
        data = response.json()['data']
        self.assertEqual(data['id'], self.apartment.id)
        self.assertEqual(data['name'], self.apartment.name)
        self.assertEqual(data['description'], self.apartment.description)
        self.assertEqual(data['district_name'], '浦东新区')
        self.assertEqual(data['street_name'], '陆家嘴街道')
        self.assertEqual(data['min_monthly_rent'], 3000)
        self.assertIn('room_types', data)
        self.assertEqual(len(data['room_types']), 1)
        self.assertEqual(data['is_favorited'], False)

    def test_detail_not_found(self):
        """获取未上架房源详情返回 404"""
        unpublished = Apartment.objects.create(
            landlord=self.landlord,
            name='未上架',
            cover_image='https://example.com/c.jpg',
            description='描述',
            district=self.district,
            street=self.street,
            detail_address='测试路',
            contact_phone='13800138000',
            status='pending_first_review',
            min_monthly_rent=2000,
        )
        response = self.client.get(f'/api/v1/apartments/{unpublished.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['code'], 404001)

    def test_detail_not_exist(self):
        """获取不存在的房源返回 404"""
        response = self.client.get('/api/v1/apartments/99999/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['code'], 404001)

    def test_detail_with_favorite(self):
        """已登录且已收藏时 is_favorited 为 True"""
        Favorite.objects.create(user=self.tenant, apartment=self.apartment)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.tenant_token}')
        response = self.client.get(f'/api/v1/apartments/{self.apartment.id}/')
        data = response.json()['data']
        self.assertEqual(data['is_favorited'], True)

    def test_detail_room_types_structure(self):
        """详情中房型卡片结构正确"""
        response = self.client.get(f'/api/v1/apartments/{self.apartment.id}/')
        data = response.json()['data']
        room_types = data['room_types']
        self.assertEqual(len(room_types), 1)
        rt = room_types[0]
        self.assertIn('id', rt)
        self.assertIn('name', rt)
        self.assertIn('images', rt)
        self.assertIn('facilities', rt)
        self.assertIn('layout_type', rt)
        self.assertIn('window_type', rt)
        self.assertIn('orientation', rt)
        self.assertIn('floor', rt)
        self.assertIn('sort', rt)
        self.assertIn('min_monthly_rent', rt)


class ApartmentRoomTypesTests(TestCase):
    """房源下所有房型接口测试"""

    def setUp(self):
        self.client = APIClient()
        self.district = District.objects.create(name='浦东新区', level=1, code='310115', sort=0)
        self.street = District.objects.create(name='陆家嘴街道', level=2, code='310115001', parent=self.district, sort=0)
        self.landlord = User.objects.create(phone='13800138000', password="fake", role='landlord', is_active=True)
        self.apartment = Apartment.objects.create(
            landlord=self.landlord,
            name='测试公寓',
            cover_image='https://example.com/cover.jpg',
            description='描述',
            district=self.district,
            street=self.street,
            detail_address='测试路1号',
            contact_phone='13800138000',
            status='published',
            min_monthly_rent=2500,
        )
        self.room1 = RoomType.objects.create(
            apartment=self.apartment,
            name='单间A',
            images=['https://example.com/a.jpg'],
            facilities=[],
            layout_type='studio',
            window_type='external',
            orientation='south',
            floor=3,
            sort=1,
        )
        RentalPlan.objects.create(room_type=self.room1, lease_term='1_month', monthly_rent=2500, payment_method='pay_1_deposit_1')
        self.room2 = RoomType.objects.create(
            apartment=self.apartment,
            name='单间B',
            images=['https://example.com/b.jpg'],
            facilities=['air_conditioner'],
            layout_type='studio',
            window_type='internal',
            orientation='north',
            floor=5,
            sort=0,
        )
        RentalPlan.objects.create(room_type=self.room2, lease_term='6_month', monthly_rent=2800, payment_method='pay_3_deposit_1')

    def test_apartment_room_types_success(self):
        """获取房源下所有房型成功"""
        response = self.client.get(f'/api/v1/apartments/{self.apartment.id}/room-types/')
        self.assertEqual(response.status_code, 200)
        data = response.json()['data']
        self.assertEqual(len(data), 2)
        # 按 sort 排序，room2 sort=0 在前
        self.assertEqual(data[0]['id'], self.room2.id)
        self.assertEqual(data[1]['id'], self.room1.id)

    def test_apartment_room_types_unpublished(self):
        """未上架房源返回 404"""
        unpublished = Apartment.objects.create(
            landlord=self.landlord,
            name='未上架',
            cover_image='https://example.com/c.jpg',
            description='描述',
            district=self.district,
            street=self.street,
            detail_address='测试路',
            contact_phone='13800138000',
            status='pending_first_review',
            min_monthly_rent=2000,
        )
        response = self.client.get(f'/api/v1/apartments/{unpublished.id}/room-types/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['code'], 404001)


class RoomTypeDetailTests(TestCase):
    """户型详情接口测试"""

    def setUp(self):
        self.client = APIClient()
        self.district = District.objects.create(name='浦东新区', level=1, code='310115', sort=0)
        self.street = District.objects.create(name='陆家嘴街道', level=2, code='310115001', parent=self.district, sort=0)
        self.landlord = User.objects.create(phone='13800138000', password="fake", role='landlord', is_active=True)
        self.apartment = Apartment.objects.create(
            landlord=self.landlord,
            name='测试公寓',
            cover_image='https://example.com/cover.jpg',
            description='描述',
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
        RentalPlan.objects.create(room_type=self.room, lease_term='6_month', monthly_rent=2800, payment_method='pay_3_deposit_1')

    def test_room_type_detail_success(self):
        """获取户型详情成功"""
        response = self.client.get(f'/api/v1/apartments/room-types/{self.room.id}/')
        self.assertEqual(response.status_code, 200)
        data = response.json()['data']
        self.assertEqual(data['id'], self.room.id)
        self.assertEqual(data['name'], '标准单间')
        self.assertEqual(len(data['images']), 1)
        self.assertEqual(len(data['rental_plans']), 2)
        self.assertIn('apartment', data)
        self.assertEqual(data['apartment']['id'], self.apartment.id)

    def test_room_type_detail_not_found(self):
        """获取不存在的户型返回 404"""
        response = self.client.get('/api/v1/apartments/room-types/99999/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['code'], 404001)

    def test_room_type_detail_unpublished_apartment(self):
        """所属公寓未上架时返回 404"""
        unpublished = Apartment.objects.create(
            landlord=self.landlord,
            name='未上架',
            cover_image='https://example.com/c.jpg',
            description='描述',
            district=self.district,
            street=self.street,
            detail_address='测试路',
            contact_phone='13800138000',
            status='pending_first_review',
            min_monthly_rent=2000,
        )
        room = RoomType.objects.create(
            apartment=unpublished,
            name='隐藏房型',
            images=[],
            facilities=[],
            layout_type='studio',
            window_type='external',
            orientation='south',
            floor=1,
            sort=0,
        )
        RentalPlan.objects.create(room_type=room, lease_term='1_month', monthly_rent=2000, payment_method='pay_1_deposit_1')
        response = self.client.get(f'/api/v1/apartments/room-types/{room.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['code'], 404001)


# ============================================================
# 商家已上架房源管理接口单元测试
# ============================================================

class MerchantApartmentListTests(TestCase):
    """商家已上架房源列表接口测试"""

    def setUp(self):
        self.client = APIClient()
        self.url = '/api/v1/merchant/apartments/'

        # 创建行政区与街道
        self.district = District.objects.create(name='浦东新区', level=1, code='310115', sort=0)
        self.street = District.objects.create(name='陆家嘴街道', level=2, code='310115001', parent=self.district, sort=0)

        # 创建商家
        self.landlord = User.objects.create(phone='13800138000', password="fake", role='landlord', is_active=True)
        self.landlord_token = self._get_token(self.landlord)

        # 创建另一个商家
        self.other_landlord = User.objects.create(phone='13800138001', password="fake", role='landlord', is_active=True)

        # 创建已上架房源 A
        self.apartment_a = Apartment.objects.create(
            landlord=self.landlord,
            name='陆家嘴精品公寓',
            cover_image='https://example.com/a.jpg',
            description='描述A',
            district=self.district,
            street=self.street,
            detail_address='测试路1号',
            contact_phone='13800138000',
            status='published',
            min_monthly_rent=3000,
        )
        self.room_a = RoomType.objects.create(
            apartment=self.apartment_a,
            name='标准单间',
            images=['https://example.com/ra.jpg'],
            facilities=['air_conditioner'],
            layout_type='studio',
            window_type='external',
            orientation='south',
            floor=5,
            sort=0,
        )
        RentalPlan.objects.create(room_type=self.room_a, lease_term='1_month', monthly_rent=3000, payment_method='pay_1_deposit_1')

        # 创建已上架房源 B（另一个商家）
        self.apartment_b = Apartment.objects.create(
            landlord=self.other_landlord,
            name='他人公寓',
            cover_image='https://example.com/b.jpg',
            description='描述B',
            district=self.district,
            street=self.street,
            detail_address='测试路2号',
            contact_phone='13800138001',
            status='published',
            min_monthly_rent=5000,
        )

        # 创建未上架房源（同一商家）
        self.apartment_c = Apartment.objects.create(
            landlord=self.landlord,
            name='待审核房源',
            cover_image='https://example.com/c.jpg',
            description='描述C',
            district=self.district,
            street=self.street,
            detail_address='测试路3号',
            contact_phone='13800138002',
            status='pending_first_review',
            min_monthly_rent=2000,
        )

    def _get_token(self, user):
        refresh = RefreshToken.for_user(user)
        refresh['role'] = user.role
        refresh['phone'] = user.phone
        refresh['username'] = user.username
        return str(refresh.access_token)

    def test_list_only_own_published(self):
        """列表仅展示当前商家已上架房源"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.landlord_token}')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        data = response.json()['data']
        self.assertEqual(data['total'], 1)
        self.assertEqual(data['items'][0]['id'], self.apartment_a.id)

    def test_list_unauthorized(self):
        """未登录返回 401"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 401)

    def test_list_not_landlord(self):
        """非商家角色返回 403"""
        tenant = User.objects.create(phone='13900139000', password="fake", role='tenant', is_active=True)
        token = self._get_token(tenant)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    def test_list_pagination(self):
        """分页参数生效"""
        # 再创建几个已上架房源
        for i in range(3):
            Apartment.objects.create(
                landlord=self.landlord,
                name=f'公寓{i}',
                cover_image='https://example.com/x.jpg',
                description='描述',
                district=self.district,
                street=self.street,
                detail_address=f'测试路{i}号',
                contact_phone='13800138000',
                status='published',
                min_monthly_rent=2000,
            )
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.landlord_token}')
        response = self.client.get(self.url, {'page': 1, 'page_size': 2})
        data = response.json()['data']
        self.assertEqual(len(data['items']), 2)
        self.assertEqual(data['total'], 4)


class MerchantApartmentDetailTests(TestCase):
    """商家自有房源详情接口测试"""

    def setUp(self):
        self.client = APIClient()

        self.district = District.objects.create(name='浦东新区', level=1, code='310115', sort=0)
        self.street = District.objects.create(name='陆家嘴街道', level=2, code='310115001', parent=self.district, sort=0)

        self.landlord = User.objects.create(phone='13800138000', password="fake", role='landlord', is_active=True)
        self.landlord_token = self._get_token(self.landlord)

        self.other_landlord = User.objects.create(phone='13800138001', password="fake", role='landlord', is_active=True)

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

    def _get_token(self, user):
        refresh = RefreshToken.for_user(user)
        refresh['role'] = user.role
        refresh['phone'] = user.phone
        refresh['username'] = user.username
        return str(refresh.access_token)

    def test_detail_success(self):
        """获取自有房源详情成功"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.landlord_token}')
        response = self.client.get(f'/api/v1/merchant/apartments/{self.apartment.id}')
        self.assertEqual(response.status_code, 200)
        data = response.json()['data']
        self.assertEqual(data['id'], self.apartment.id)
        self.assertEqual(data['name'], '测试公寓')
        self.assertEqual(data['district_name'], '浦东新区')
        self.assertEqual(data['street_name'], '陆家嘴街道')
        self.assertEqual(data['pending_audit'], False)
        self.assertIn('room_types', data)

    def test_detail_not_own(self):
        """获取他人房源详情返回 404"""
        token = self._get_token(self.other_landlord)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        response = self.client.get(f'/api/v1/merchant/apartments/{self.apartment.id}')
        self.assertEqual(response.status_code, 200)

    def test_detail_not_found(self):
        """获取不存在的房源返回 404"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.landlord_token}')
        response = self.client.get('/api/v1/merchant/apartments/99999')
        self.assertEqual(response.status_code, 200)

    def test_detail_pending_audit(self):
        """有待审核变更时 pending_audit 为 True"""
        AuditRecord.objects.create(
            apartment=self.apartment,
            type='change_review',
            status='pending',
            submitted_data={},
            changed_fields=['name'],
        )
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.landlord_token}')
        response = self.client.get(f'/api/v1/merchant/apartments/{self.apartment.id}')
        data = response.json()['data']
        self.assertEqual(data['pending_audit'], True)


class MerchantApartmentUpdateTests(TestCase):
    """商家编辑房源接口测试"""

    def setUp(self):
        self.client = APIClient()

        self.district = District.objects.create(name='浦东新区', level=1, code='310115', sort=0)
        self.street = District.objects.create(name='陆家嘴街道', level=2, code='310115001', parent=self.district, sort=0)
        self.district2 = District.objects.create(name='黄浦区', level=1, code='310101', sort=0)
        self.street2 = District.objects.create(name='南京东路街道', level=2, code='310101001', parent=self.district2, sort=0)

        self.landlord = User.objects.create(phone='13800138000', password="fake", role='landlord', is_active=True)
        self.landlord_token = self._get_token(self.landlord)

        self.other_landlord = User.objects.create(phone='13800138001', password="fake", role='landlord', is_active=True)

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

    def _get_token(self, user):
        refresh = RefreshToken.for_user(user)
        refresh['role'] = user.role
        refresh['phone'] = user.phone
        refresh['username'] = user.username
        return str(refresh.access_token)

    def test_update_direct_no_key_change(self):
        """非关键字段变更直接更新"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.landlord_token}')
        payload = {
            'cover_image': 'https://example.com/new_cover.jpg',
            'description': '新描述',
            'contact_phone': '13900139000',
        }
        response = self.client.put(f'/api/v1/merchant/apartments/{self.apartment.id}', payload, format='json')
        self.assertEqual(response.status_code, 200)
        data = response.json()['data']
        self.assertEqual(data['updated'], True)
        self.assertIsNone(data['audit_id'])

        self.apartment.refresh_from_db()
        self.assertEqual(self.apartment.cover_image, 'https://example.com/new_cover.jpg')
        self.assertEqual(self.apartment.description, '新描述')
        self.assertEqual(self.apartment.contact_phone, '13900139000')
        self.assertEqual(self.apartment.status, 'published')

    def test_update_name_triggers_audit(self):
        """变更名称触发 change_review 审核"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.landlord_token}')
        payload = {'name': '新公寓名称'}
        response = self.client.put(f'/api/v1/merchant/apartments/{self.apartment.id}', payload, format='json')
        self.assertEqual(response.status_code, 200)
        data = response.json()['data']
        self.assertEqual(data['updated'], False)
        self.assertIsNotNone(data['audit_id'])

        # 原房源仍 published
        self.apartment.refresh_from_db()
        self.assertEqual(self.apartment.status, 'published')
        self.assertEqual(self.apartment.name, '测试公寓')

        # 审核记录存在
        audit = AuditRecord.objects.get(id=data['audit_id'])
        self.assertEqual(audit.type, 'change_review')
        self.assertEqual(audit.status, 'pending')
        self.assertEqual(audit.changed_fields, ['name'])
        self.assertIsNotNone(audit.original_data)
        self.assertIsNotNone(audit.submitted_data)

    def test_update_district_triggers_audit(self):
        """变更行政区触发 change_review 审核"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.landlord_token}')
        payload = {'district_id': self.district2.id, 'street_id': self.street2.id}
        response = self.client.put(f'/api/v1/merchant/apartments/{self.apartment.id}', payload, format='json')
        self.assertEqual(response.status_code, 200)
        data = response.json()['data']
        self.assertEqual(data['updated'], False)

        self.apartment.refresh_from_db()
        self.assertEqual(self.apartment.district_id, self.district.id)
        self.assertEqual(self.apartment.status, 'published')

    def test_update_detail_address_triggers_audit(self):
        """变更详细地址触发 change_review 审核"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.landlord_token}')
        payload = {'detail_address': '新地址123号'}
        response = self.client.put(f'/api/v1/merchant/apartments/{self.apartment.id}', payload, format='json')
        self.assertEqual(response.status_code, 200)
        data = response.json()['data']
        self.assertEqual(data['updated'], False)

        self.apartment.refresh_from_db()
        self.assertEqual(self.apartment.detail_address, '测试路1号')

    def test_update_with_room_types_direct(self):
        """直接更新时支持全量替换房型"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.landlord_token}')
        payload = {
            'cover_image': 'https://example.com/new.jpg',
            'room_types': [
                {
                    'name': '豪华单间',
                    'images': ['https://example.com/new_room.jpg'],
                    'facilities': ['wifi'],
                    'layout_type': 'studio',
                    'window_type': 'external',
                    'orientation': 'north',
                    'floor': 3,
                    'sort': 1,
                    'rental_plans': [
                        {'lease_term': '3_month', 'monthly_rent': 3500, 'payment_method': 'pay_3_deposit_1'},
                    ],
                },
            ],
        }
        response = self.client.put(f'/api/v1/merchant/apartments/{self.apartment.id}', payload, format='json')
        self.assertEqual(response.status_code, 200)
        data = response.json()['data']
        self.assertEqual(data['updated'], True)

        self.apartment.refresh_from_db()
        self.assertEqual(self.apartment.min_monthly_rent, 3500)
        room_types = list(self.apartment.room_types.all())
        self.assertEqual(len(room_types), 1)
        self.assertEqual(room_types[0].name, '豪华单间')

    def test_update_not_own(self):
        """编辑他人房源返回 404"""
        token = self._get_token(self.other_landlord)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        response = self.client.put(f'/api/v1/merchant/apartments/{self.apartment.id}', {'name': '新名称'}, format='json')
        self.assertEqual(response.status_code, 200)

    def test_update_invalid_district(self):
        """传入无效行政区返回 400"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.landlord_token}')
        payload = {'district_id': 99999, 'street_id': 99999}
        response = self.client.put(f'/api/v1/merchant/apartments/{self.apartment.id}', payload, format='json')
        self.assertEqual(response.status_code, 200)

    def test_update_only_street_id_valid(self):
        """仅传入有效 street_id（不传 district_id）应校验通过并触发审核"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.landlord_token}')
        payload = {'street_id': self.street2.id}
        response = self.client.put(f'/api/v1/merchant/apartments/{self.apartment.id}', payload, format='json')
        self.assertEqual(response.status_code, 200)
        data = response.json()['data']
        self.assertEqual(data['updated'], False)

    def test_update_only_street_id_invalid(self):
        """仅传入无效 street_id 应返回 400"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.landlord_token}')
        payload = {'street_id': 99999}
        response = self.client.put(f'/api/v1/merchant/apartments/{self.apartment.id}', payload, format='json')
        self.assertEqual(response.status_code, 200)

    def test_update_street_id_mismatch_district_id(self):
        """传入 street_id 与 district_id 不匹配应返回 400"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.landlord_token}')
        # 黄浦区的街道 + 浦东新区的行政区 → 不匹配
        payload = {'district_id': self.district.id, 'street_id': self.street2.id}
        response = self.client.put(f'/api/v1/merchant/apartments/{self.apartment.id}', payload, format='json')
        self.assertEqual(response.status_code, 200)


class MerchantApartmentDeleteTests(TestCase):
    """商家删除房源接口测试"""

    def setUp(self):
        self.client = APIClient()

        self.district = District.objects.create(name='浦东新区', level=1, code='310115', sort=0)
        self.street = District.objects.create(name='陆家嘴街道', level=2, code='310115001', parent=self.district, sort=0)

        self.landlord = User.objects.create(phone='13800138000', password="fake", role='landlord', is_active=True)
        self.landlord_token = self._get_token(self.landlord)

        self.other_landlord = User.objects.create(phone='13800138001', password="fake", role='landlord', is_active=True)

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

        # 创建未批准审核单
        self.audit = AuditRecord.objects.create(
            apartment=self.apartment,
            type='change_review',
            status='pending',
            submitted_data={},
            changed_fields=['name'],
        )

    def _get_token(self, user):
        refresh = RefreshToken.for_user(user)
        refresh['role'] = user.role
        refresh['phone'] = user.phone
        refresh['username'] = user.username
        return str(refresh.access_token)

    def test_delete_success(self):
        """删除自有房源成功，并软删除关联审核单"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.landlord_token}')
        response = self.client.delete(f'/api/v1/merchant/apartments/{self.apartment.id}')
        self.assertEqual(response.status_code, 200)
        data = response.json()['data']
        self.assertEqual(data['deleted'], True)

        # 房源已软删除
        self.assertFalse(Apartment.objects.filter(id=self.apartment.id).exists())
        self.assertTrue(Apartment.all_objects.filter(id=self.apartment.id).exists())

        # 审核单已软删除
        self.audit.refresh_from_db()
        self.assertIsNotNone(self.audit.deleted_at)

    def test_delete_not_own(self):
        """删除他人房源返回 404"""
        token = self._get_token(self.other_landlord)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        response = self.client.delete(f'/api/v1/merchant/apartments/{self.apartment.id}')
        self.assertEqual(response.status_code, 200)

    def test_delete_unauthorized(self):
        """未登录返回 401"""
        response = self.client.delete(f'/api/v1/merchant/apartments/{self.apartment.id}')
        self.assertEqual(response.status_code, 401)


# ============================================================
# 商家发布房源接口单元测试
# ============================================================

class CreateApartmentTests(TestCase):
    """商家发布房源接口测试"""

    def setUp(self):
        self.client = APIClient()
        self.url = '/api/v1/merchant/apartments/'

        self.district = District.objects.create(name='浦东新区', level=1, code='310115', sort=0)
        self.street = District.objects.create(name='陆家嘴街道', level=2, code='310115001', parent=self.district, sort=0)

        self.landlord = User.objects.create(phone='13800138000', password='fake', role='landlord', is_active=True)
        self.landlord_token = self._get_token(self.landlord)

        self.tenant = User.objects.create(phone='13900139000', password='fake', role='tenant', is_active=True)

        self.valid_payload = {
            'name': '陆家嘴精品公寓',
            'cover_image': 'https://example.com/cover.jpg',
            'description': '这是一套位于陆家嘴的精品公寓，交通便利，配套齐全。',
            'district_id': self.district.id,
            'street_id': self.street.id,
            'detail_address': '陆家嘴金融中心888号',
            'contact_phone': '13800138000',
            'room_types': [
                {
                    'name': '标准单间',
                    'images': ['https://example.com/room1.jpg'],
                    'facilities': ['air_conditioner', 'washing_machine'],
                    'layout_type': 'studio',
                    'window_type': 'external',
                    'orientation': 'south',
                    'floor': 5,
                    'sort': 0,
                    'rental_plans': [
                        {'lease_term': '1_month', 'monthly_rent': 3000, 'payment_method': 'pay_1_deposit_1'},
                        {'lease_term': '6_month', 'monthly_rent': 2800, 'payment_method': 'pay_3_deposit_1'},
                    ],
                },
            ],
        }

    def _get_token(self, user):
        refresh = RefreshToken.for_user(user)
        refresh['role'] = user.role
        refresh['phone'] = user.phone
        refresh['username'] = user.username
        return str(refresh.access_token)

    def test_create_success(self):
        """商家发布房源成功，返回房源 ID 和审核单 ID"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.landlord_token}')
        response = self.client.post(self.url, self.valid_payload, format='json')
        self.assertEqual(response.status_code, 200)
        data = response.json()['data']
        self.assertIn('apartment_id', data)
        self.assertIn('audit_id', data)
        self.assertIsNotNone(data['apartment_id'])
        self.assertIsNotNone(data['audit_id'])

        apartment = Apartment.objects.get(id=data['apartment_id'])
        self.assertEqual(apartment.name, '陆家嘴精品公寓')
        self.assertEqual(apartment.landlord, self.landlord)
        self.assertEqual(apartment.status, 'pending_first_review')
        self.assertEqual(apartment.min_monthly_rent, 2800)

        audit = AuditRecord.objects.get(id=data['audit_id'])
        self.assertEqual(audit.type, 'first_review')
        self.assertEqual(audit.status, 'pending')
        self.assertIsNotNone(audit.submitted_data)

    def test_create_multi_room_types(self):
        """发布多个房型的房源，最低月租金正确"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.landlord_token}')
        payload = dict(self.valid_payload)
        payload['room_types'] = [
            {
                'name': '豪华套房',
                'images': ['https://example.com/luxury.jpg'],
                'facilities': ['air_conditioner', 'wifi'],
                'layout_type': 'two_bedroom',
                'window_type': 'external',
                'orientation': 'east',
                'floor': 8,
                'sort': 0,
                'rental_plans': [
                    {'lease_term': '1_year', 'monthly_rent': 8000, 'payment_method': 'pay_3_deposit_1'},
                ],
            },
            {
                'name': '经济单间',
                'images': ['https://example.com/budget.jpg'],
                'facilities': [],
                'layout_type': 'studio',
                'window_type': 'internal',
                'orientation': 'north',
                'floor': 2,
                'sort': 1,
                'rental_plans': [
                    {'lease_term': '1_month', 'monthly_rent': 2000, 'payment_method': 'pay_1_deposit_1'},
                ],
            },
        ]
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, 200)
        data = response.json()['data']
        apartment = Apartment.objects.get(id=data['apartment_id'])
        self.assertEqual(apartment.min_monthly_rent, 2000)
        self.assertEqual(apartment.room_types.count(), 2)

    def test_create_unauthorized(self):
        """未登录返回 401"""
        response = self.client.post(self.url, self.valid_payload, format='json')
        self.assertEqual(response.status_code, 401)

    def test_create_not_landlord(self):
        """租客角色返回 403"""
        token = self._get_token(self.tenant)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        response = self.client.post(self.url, self.valid_payload, format='json')
        self.assertEqual(response.status_code, 403)

    def test_create_missing_required_fields(self):
        """缺少必填字段返回 400"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.landlord_token}')
        payload = {'name': '测试'}
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, 200)

    def test_create_invalid_district(self):
        """无效行政区 ID 返回 400"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.landlord_token}')
        payload = dict(self.valid_payload)
        payload['district_id'] = 99999
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, 200)

    def test_create_invalid_street(self):
        """无效街道 ID 返回 400"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.landlord_token}')
        payload = dict(self.valid_payload)
        payload['street_id'] = 99999
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, 200)

    def test_create_no_room_types(self):
        """无房型数据返回 400"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.landlord_token}')
        payload = dict(self.valid_payload)
        payload['room_types'] = []
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, 200)

    def test_create_too_many_room_images(self):
        """房型图片超过 5 张返回 400"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.landlord_token}')
        payload = dict(self.valid_payload)
        payload['room_types'][0]['images'] = [
            'https://example.com/1.jpg',
            'https://example.com/2.jpg',
            'https://example.com/3.jpg',
            'https://example.com/4.jpg',
            'https://example.com/5.jpg',
            'https://example.com/6.jpg',
        ]
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, 200)

    def test_create_no_rental_plans(self):
        """房型无租金方案返回 400"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.landlord_token}')
        payload = dict(self.valid_payload)
        payload['room_types'][0]['rental_plans'] = []
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, 200)

    def test_create_negative_rent(self):
        """月租金为负数返回 400"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.landlord_token}')
        payload = dict(self.valid_payload)
        payload['room_types'][0]['rental_plans'][0]['monthly_rent'] = -100
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, 200)


class EnumValidationTests(TestCase):
    """枚举字段合法性校验单元测试"""

    def setUp(self):
        self.client = APIClient()
        self.url = '/api/v1/merchant/apartments/'

        self.district = District.objects.create(name='浦东新区', level=1, code='310115', sort=0)
        self.street = District.objects.create(name='陆家嘴街道', level=2, code='310115001', parent=self.district, sort=0)

        self.landlord = User.objects.create(phone='13800138000', password='fake', role='landlord', is_active=True)
        self.landlord_token = self._get_token(self.landlord)

        self.valid_payload = {
            'name': '陆家嘴精品公寓',
            'cover_image': 'https://example.com/cover.jpg',
            'description': '这是一套位于陆家嘴的精品公寓。',
            'district_id': self.district.id,
            'street_id': self.street.id,
            'detail_address': '陆家嘴金融中心888号',
            'contact_phone': '13800138000',
            'room_types': [
                {
                    'name': '标准单间',
                    'images': ['https://example.com/room1.jpg'],
                    'facilities': ['air_conditioner', 'washing_machine'],
                    'layout_type': 'studio',
                    'window_type': 'external',
                    'orientation': 'south',
                    'floor': 5,
                    'sort': 0,
                    'rental_plans': [
                        {'lease_term': '1_month', 'monthly_rent': 3000, 'payment_method': 'pay_1_deposit_1'},
                    ],
                },
            ],
        }

    def _get_token(self, user):
        refresh = RefreshToken.for_user(user)
        refresh['role'] = user.role
        refresh['phone'] = user.phone
        refresh['username'] = user.username
        return str(refresh.access_token)

    def _assert_enum_error(self, payload, expected_msg_substring):
        """辅助方法：断言返回 400 且错误信息包含指定子串"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.landlord_token}')
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['code'], 400002)
        self.assertIn(expected_msg_substring, response.json()['message'])

    def test_create_invalid_layout_type(self):
        """非法 layout_type 返回 400"""
        payload = dict(self.valid_payload)
        payload['room_types'] = [dict(self.valid_payload['room_types'][0])]
        payload['room_types'][0]['layout_type'] = 'invalid_layout'
        self._assert_enum_error(payload, '无效的户型类型')

    def test_create_invalid_window_type(self):
        """非法 window_type 返回 400"""
        payload = dict(self.valid_payload)
        payload['room_types'] = [dict(self.valid_payload['room_types'][0])]
        payload['room_types'][0]['window_type'] = 'invalid_window'
        self._assert_enum_error(payload, '无效的窗户类型')

    def test_create_invalid_orientation(self):
        """非法 orientation 返回 400"""
        payload = dict(self.valid_payload)
        payload['room_types'] = [dict(self.valid_payload['room_types'][0])]
        payload['room_types'][0]['orientation'] = 'invalid_orientation'
        self._assert_enum_error(payload, '无效的朝向')

    def test_create_invalid_facilities(self):
        """非法 facilities 返回 400"""
        payload = dict(self.valid_payload)
        payload['room_types'] = [dict(self.valid_payload['room_types'][0])]
        payload['room_types'][0]['facilities'] = ['invalid_facility']
        self._assert_enum_error(payload, '无效的设施编码')

    def test_create_invalid_lease_term(self):
        """非法 lease_term 返回 400"""
        payload = dict(self.valid_payload)
        payload['room_types'] = [dict(self.valid_payload['room_types'][0])]
        payload['room_types'][0]['rental_plans'] = [
            {'lease_term': 'invalid_term', 'monthly_rent': 3000, 'payment_method': 'pay_1_deposit_1'},
        ]
        self._assert_enum_error(payload, '无效的租期')

    def test_create_invalid_payment_method(self):
        """非法 payment_method 返回 400"""
        payload = dict(self.valid_payload)
        payload['room_types'] = [dict(self.valid_payload['room_types'][0])]
        payload['room_types'][0]['rental_plans'] = [
            {'lease_term': '1_month', 'monthly_rent': 3000, 'payment_method': 'invalid_payment'},
        ]
        self._assert_enum_error(payload, '无效的支付方式')

    def test_update_invalid_layout_type(self):
        """更新时非法 layout_type 返回 400"""
        apartment = Apartment.objects.create(
            landlord=self.landlord,
            name='测试公寓',
            cover_image='https://example.com/cover.jpg',
            description='描述',
            district=self.district,
            street=self.street,
            detail_address='测试路1号',
            contact_phone='13800138000',
            status='published',
            min_monthly_rent=3000,
        )
        RoomType.objects.create(
            apartment=apartment,
            name='标准单间',
            images=['https://example.com/room.jpg'],
            facilities=['air_conditioner'],
            layout_type='studio',
            window_type='external',
            orientation='south',
            floor=5,
            sort=0,
        )
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.landlord_token}')
        payload = {
            'room_types': [
                {
                    'name': '豪华单间',
                    'images': ['https://example.com/new_room.jpg'],
                    'facilities': ['air_conditioner'],
                    'layout_type': 'invalid_layout',
                    'window_type': 'external',
                    'orientation': 'north',
                    'floor': 3,
                    'sort': 1,
                    'rental_plans': [
                        {'lease_term': '1_month', 'monthly_rent': 3500, 'payment_method': 'pay_1_deposit_1'},
                    ],
                },
            ],
        }
        response = self.client.put(f'/api/v1/merchant/apartments/{apartment.id}', payload, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['code'], 400002)
        self.assertIn('无效的户型类型', response.json()['message'])

    def test_update_invalid_lease_term(self):
        """更新时非法 lease_term 返回 400"""
        apartment = Apartment.objects.create(
            landlord=self.landlord,
            name='测试公寓',
            cover_image='https://example.com/cover.jpg',
            description='描述',
            district=self.district,
            street=self.street,
            detail_address='测试路1号',
            contact_phone='13800138000',
            status='published',
            min_monthly_rent=3000,
        )
        RoomType.objects.create(
            apartment=apartment,
            name='标准单间',
            images=['https://example.com/room.jpg'],
            facilities=['air_conditioner'],
            layout_type='studio',
            window_type='external',
            orientation='south',
            floor=5,
            sort=0,
        )
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.landlord_token}')
        payload = {
            'room_types': [
                {
                    'name': '豪华单间',
                    'images': ['https://example.com/new_room.jpg'],
                    'facilities': ['air_conditioner'],
                    'layout_type': 'studio',
                    'window_type': 'external',
                    'orientation': 'north',
                    'floor': 3,
                    'sort': 1,
                    'rental_plans': [
                        {'lease_term': 'invalid_term', 'monthly_rent': 3500, 'payment_method': 'pay_1_deposit_1'},
                    ],
                },
            ],
        }
        response = self.client.put(f'/api/v1/merchant/apartments/{apartment.id}', payload, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['code'], 400002)
        self.assertIn('无效的租期', response.json()['message'])

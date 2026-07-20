"""
房源发布接口单元测试
"""
import json
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.users.models import User
from apps.districts.models import District
from apps.apartments.models import Apartment, RoomType, RentalPlan
from apps.audits.models import AuditRecord


class CreateApartmentTests(TestCase):
    """商家发布房源接口测试"""

    def setUp(self):
        self.client = APIClient()
        # 创建行政区（level=1）
        self.district = District.objects.create(
            name='浦东新区',
            level=1,
            code='310115',
            sort=0,
        )
        # 创建街道（level=2）
        self.street = District.objects.create(
            name='陆家嘴街道',
            level=2,
            code='310115001',
            parent=self.district,
            sort=0,
        )
        # 创建商家用户
        self.landlord = User.objects.create(
            phone='13800138000',
            hashed_password='fake_hash',
            role='landlord',
            is_active=True,
        )
        # 创建租客用户
        self.tenant = User.objects.create(
            phone='13800138001',
            hashed_password='fake_hash',
            role='tenant',
            is_active=True,
        )
        # 创建无角色用户
        self.no_role_user = User.objects.create(
            phone='13800138002',
            hashed_password='fake_hash',
            role='',
            is_active=True,
        )

        # 生成 JWT token
        self.landlord_token = self._get_token(self.landlord)
        self.tenant_token = self._get_token(self.tenant)
        self.no_role_token = self._get_token(self.no_role_user)

        self.url = '/api/v1/merchant/apartments/'

        self.valid_payload = {
            'name': '测试公寓',
            'cover_image': 'https://example.com/cover.jpg',
            'description': '这是一套测试公寓，描述不超过500字。',
            'district_id': self.district.id,
            'street_id': self.street.id,
            'detail_address': '测试路 123 号',
            'contact_phone': '13800138000',
            'room_types': [
                {
                    'name': '标准单间',
                    'images': [
                        'https://example.com/room1.jpg',
                        'https://example.com/room2.jpg',
                    ],
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
                }
            ],
        }

    def _get_token(self, user):
        refresh = RefreshToken.for_user(user)
        refresh['role'] = user.role
        refresh['phone'] = user.phone
        refresh['username'] = user.username
        return str(refresh.access_token)

    def test_create_apartment_success(self):
        """合法请求：商家发布房源成功，返回 apartment_id 与 audit_id"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.landlord_token}')
        response = self.client.post(self.url, data=self.valid_payload, format='json')

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['code'], 0)
        self.assertIn('apartment_id', data['data'])
        self.assertIn('audit_id', data['data'])

        apartment_id = data['data']['apartment_id']
        audit_id = data['data']['audit_id']

        # 校验公寓状态
        apartment = Apartment.objects.get(id=apartment_id)
        self.assertEqual(apartment.status, 'pending_first_review')
        self.assertEqual(apartment.landlord_id, self.landlord.id)
        self.assertEqual(apartment.min_monthly_rent, 2800)  # 最低租金

        # 校验房型
        room_types = RoomType.objects.filter(apartment=apartment)
        self.assertEqual(room_types.count(), 1)
        rt = room_types.first()
        self.assertEqual(rt.name, '标准单间')
        self.assertEqual(len(rt.images), 2)

        # 校验租金方案
        plans = RentalPlan.objects.filter(room_type=rt)
        self.assertEqual(plans.count(), 2)

        # 校验审核记录
        audit = AuditRecord.objects.get(id=audit_id)
        self.assertEqual(audit.type, 'first_review')
        self.assertEqual(audit.status, 'pending')
        self.assertIn('room_types', audit.submitted_data)
        self.assertEqual(audit.apartment_id, apartment_id)

    def test_create_apartment_multiple_room_types(self):
        """多房型发布成功"""
        payload = self.valid_payload.copy()
        payload['room_types'] = [
            {
                'name': '标准单间',
                'images': ['https://example.com/room1.jpg'],
                'facilities': [],
                'layout_type': 'studio',
                'window_type': 'external',
                'orientation': 'south',
                'floor': 5,
                'sort': 0,
                'rental_plans': [
                    {'lease_term': '1_month', 'monthly_rent': 3000, 'payment_method': 'pay_1_deposit_1'},
                ],
            },
            {
                'name': '豪华套房',
                'images': ['https://example.com/room3.jpg'],
                'facilities': ['air_conditioner'],
                'layout_type': 'two_bedroom',
                'window_type': 'external',
                'orientation': 'east',
                'floor': 8,
                'sort': 1,
                'rental_plans': [
                    {'lease_term': '1_year', 'monthly_rent': 5000, 'payment_method': 'pay_3_deposit_1'},
                ],
            },
        ]

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.landlord_token}')
        response = self.client.post(self.url, data=payload, format='json')

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['code'], 0)

        apartment = Apartment.objects.get(id=data['data']['apartment_id'])
        self.assertEqual(apartment.min_monthly_rent, 3000)  # 最低租金是 3000
        self.assertEqual(RoomType.objects.filter(apartment=apartment).count(), 2)

    def test_create_apartment_no_room_types(self):
        """缺少房型：返回 400002"""
        payload = self.valid_payload.copy()
        payload['room_types'] = []

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.landlord_token}')
        response = self.client.post(self.url, data=payload, format='json')

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data['code'], 400002)

    def test_create_apartment_missing_room_type_name(self):
        """房型字段不合法：返回 400002"""
        payload = self.valid_payload.copy()
        payload['room_types'] = [
            {
                'name': '',
                'images': [],
                'layout_type': 'studio',
                'window_type': 'external',
                'orientation': 'south',
                'floor': 5,
                'rental_plans': [
                    {'lease_term': '1_month', 'monthly_rent': 3000, 'payment_method': 'pay_1_deposit_1'},
                ],
            }
        ]

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.landlord_token}')
        response = self.client.post(self.url, data=payload, format='json')

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data['code'], 400002)

    def test_create_apartment_images_over_limit(self):
        """房型图片超过 5 张：返回 400002"""
        payload = self.valid_payload.copy()
        payload['room_types'] = [
            {
                'name': '标准单间',
                'images': [
                    'https://example.com/1.jpg',
                    'https://example.com/2.jpg',
                    'https://example.com/3.jpg',
                    'https://example.com/4.jpg',
                    'https://example.com/5.jpg',
                    'https://example.com/6.jpg',
                ],
                'layout_type': 'studio',
                'window_type': 'external',
                'orientation': 'south',
                'floor': 5,
                'rental_plans': [
                    {'lease_term': '1_month', 'monthly_rent': 3000, 'payment_method': 'pay_1_deposit_1'},
                ],
            }
        ]

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.landlord_token}')
        response = self.client.post(self.url, data=payload, format='json')

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data['code'], 400002)

    def test_create_apartment_no_rental_plans(self):
        """缺少租期租金方案：返回 400002"""
        payload = self.valid_payload.copy()
        payload['room_types'] = [
            {
                'name': '标准单间',
                'images': ['https://example.com/room1.jpg'],
                'layout_type': 'studio',
                'window_type': 'external',
                'orientation': 'south',
                'floor': 5,
                'rental_plans': [],
            }
        ]

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.landlord_token}')
        response = self.client.post(self.url, data=payload, format='json')

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data['code'], 400002)

    def test_create_apartment_invalid_district(self):
        """无效行政区：返回 400002"""
        payload = self.valid_payload.copy()
        payload['district_id'] = 99999

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.landlord_token}')
        response = self.client.post(self.url, data=payload, format='json')

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data['code'], 400002)

    def test_create_apartment_invalid_street(self):
        """无效街道：返回 400002"""
        # 创建一个不属于该行政区的街道
        other_district = District.objects.create(name='黄浦区', level=1, code='310101', sort=0)
        other_street = District.objects.create(name='南京东路街道', level=2, code='310101001', parent=other_district, sort=0)

        payload = self.valid_payload.copy()
        payload['street_id'] = other_street.id

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.landlord_token}')
        response = self.client.post(self.url, data=payload, format='json')

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data['code'], 400002)

    def test_tenant_forbidden(self):
        """租客调用：返回 403001"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.tenant_token}')
        response = self.client.post(self.url, data=self.valid_payload, format='json')

        self.assertEqual(response.status_code, 403)
        data = response.json()
        self.assertEqual(data['code'], 403001)

    def test_no_role_forbidden(self):
        """无角色用户调用：返回 403001"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.no_role_token}')
        response = self.client.post(self.url, data=self.valid_payload, format='json')

        self.assertEqual(response.status_code, 403)
        data = response.json()
        self.assertEqual(data['code'], 403001)

    def test_unauthenticated(self):
        """未登录调用：返回 401001"""
        self.client.credentials()  # 清除认证
        response = self.client.post(self.url, data=self.valid_payload, format='json')

        self.assertEqual(response.status_code, 401)
        data = response.json()
        self.assertEqual(data['code'], 401001)

    def test_apartment_name_too_short(self):
        """公寓名称少于 2 字：返回 400002"""
        payload = self.valid_payload.copy()
        payload['name'] = 'A'

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.landlord_token}')
        response = self.client.post(self.url, data=payload, format='json')

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data['code'], 400002)

    def test_description_over_limit(self):
        """描述超过 500 字：返回 400002"""
        payload = self.valid_payload.copy()
        payload['description'] = 'A' * 501

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.landlord_token}')
        response = self.client.post(self.url, data=payload, format='json')

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data['code'], 400002)

    def test_contact_phone_invalid(self):
        """联系电话非 11 位：返回 400002"""
        payload = self.valid_payload.copy()
        payload['contact_phone'] = '12345'

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.landlord_token}')
        response = self.client.post(self.url, data=payload, format='json')

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data['code'], 400002)

    def test_floor_invalid(self):
        """楼层小于 1：返回 400002"""
        payload = self.valid_payload.copy()
        payload['room_types'] = [
            {
                'name': '标准单间',
                'images': ['https://example.com/room1.jpg'],
                'layout_type': 'studio',
                'window_type': 'external',
                'orientation': 'south',
                'floor': 0,
                'rental_plans': [
                    {'lease_term': '1_month', 'monthly_rent': 3000, 'payment_method': 'pay_1_deposit_1'},
                ],
            }
        ]

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.landlord_token}')
        response = self.client.post(self.url, data=payload, format='json')

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data['code'], 400002)

    def test_monthly_rent_invalid(self):
        """月租金小于等于 0：返回 400002"""
        payload = self.valid_payload.copy()
        payload['room_types'] = [
            {
                'name': '标准单间',
                'images': ['https://example.com/room1.jpg'],
                'layout_type': 'studio',
                'window_type': 'external',
                'orientation': 'south',
                'floor': 5,
                'rental_plans': [
                    {'lease_term': '1_month', 'monthly_rent': 0, 'payment_method': 'pay_1_deposit_1'},
                ],
            }
        ]

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.landlord_token}')
        response = self.client.post(self.url, data=payload, format='json')

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data['code'], 400002)

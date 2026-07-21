"""
管理员审核接口单元测试
"""
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.users.models import User
from apps.districts.models import District
from apps.apartments.models import Apartment, RoomType, RentalPlan
from apps.audits.models import AuditRecord
from apps.messages_app.models import Message


class MerchantAuditListTests(TestCase):
    """商家审核记录列表接口测试"""

    def setUp(self):
        self.client = APIClient()
        self.url = '/api/v1/merchant/audits/'

        # 行政区与街道
        self.district = District.objects.create(name='浦东新区', level=1, code='310115', sort=0)
        self.street = District.objects.create(name='陆家嘴街道', level=2, code='310115001', parent=self.district, sort=0)

        # 商家A
        self.landlord_a = User.objects.create(phone='13800138000', hashed_password='fake', role='landlord', is_active=True)
        self.landlord_a_token = self._get_token(self.landlord_a)

        # 商家B
        self.landlord_b = User.objects.create(phone='13800138001', hashed_password='fake', role='landlord', is_active=True)
        self.landlord_b_token = self._get_token(self.landlord_b)

        # 管理员
        self.admin = User.objects.create(username='admin123', hashed_password='fake', role='admin', is_active=True)
        self.admin_token = self._get_token(self.admin)

        # 租客
        self.tenant = User.objects.create(phone='13900139000', hashed_password='fake', role='tenant', is_active=True)
        self.tenant_token = self._get_token(self.tenant)

        # 商家A的房源与审核单
        self.apartment_a1 = Apartment.objects.create(
            landlord=self.landlord_a,
            name='商家A公寓1',
            cover_image='https://example.com/cover.jpg',
            description='描述',
            district=self.district,
            street=self.street,
            detail_address='测试路1号',
            contact_phone='13800138000',
            status='pending_first_review',
        )
        self.audit_a1 = AuditRecord.objects.create(
            apartment=self.apartment_a1,
            type='first_review',
            status='pending',
            submitted_data={},
        )

        self.apartment_a2 = Apartment.objects.create(
            landlord=self.landlord_a,
            name='商家A公寓2',
            cover_image='https://example.com/cover2.jpg',
            description='描述2',
            district=self.district,
            street=self.street,
            detail_address='测试路2号',
            contact_phone='13800138000',
            status='published',
        )
        self.audit_a2 = AuditRecord.objects.create(
            apartment=self.apartment_a2,
            type='change_review',
            status='rejected',
            submitted_data={'name': '新名称'},
            original_data={'name': '商家A公寓2'},
            changed_fields=['name'],
            reject_reason='名称不符合规范',
        )

        # 商家B的房源与审核单
        self.apartment_b1 = Apartment.objects.create(
            landlord=self.landlord_b,
            name='商家B公寓1',
            cover_image='https://example.com/cover3.jpg',
            description='描述3',
            district=self.district,
            street=self.street,
            detail_address='测试路3号',
            contact_phone='13800138001',
            status='pending_first_review',
        )
        self.audit_b1 = AuditRecord.objects.create(
            apartment=self.apartment_b1,
            type='first_review',
            status='pending',
            submitted_data={},
        )

    def _get_token(self, user):
        refresh = RefreshToken.for_user(user)
        refresh['role'] = user.role
        refresh['phone'] = user.phone
        refresh['username'] = user.username
        return str(refresh.access_token)

    def test_list_success(self):
        """商家可查看自有审核记录列表"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.landlord_a_token}')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        data = response.json()['data']
        self.assertEqual(data['total'], 2)
        # 按 created_at 倒序，audit_a2 后创建排前面
        ids = [item['id'] for item in data['items']]
        self.assertEqual(ids, [self.audit_a2.id, self.audit_a1.id])

    def test_list_only_own_records(self):
        """商家只能查看自己的房源审核记录"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.landlord_a_token}')
        response = self.client.get(self.url)
        data = response.json()['data']
        self.assertEqual(data['total'], 2)
        for item in data['items']:
            self.assertIn(item['apartment_name'], ['商家A公寓1', '商家A公寓2'])

    def test_list_pagination(self):
        """分页参数生效"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.landlord_a_token}')
        response = self.client.get(self.url, {'page': 1, 'page_size': 1})
        data = response.json()['data']
        self.assertEqual(data['total'], 2)
        self.assertEqual(len(data['items']), 1)
        self.assertEqual(data['page'], 1)
        self.assertEqual(data['page_size'], 1)

    def test_list_unauthorized(self):
        """未登录返回 401"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 401)

    def test_list_not_landlord(self):
        """非商家（租客/管理员）返回 403"""
        # 租客
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.tenant_token}')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

        # 管理员
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    def test_list_order_by_created_at_desc(self):
        """列表按提交时间倒序"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.landlord_a_token}')
        response = self.client.get(self.url)
        data = response.json()['data']
        items = data['items']
        ids = [item['id'] for item in items]
        self.assertEqual(ids, sorted(ids, reverse=True))

    def test_list_fields(self):
        """返回字段与前端 MyApartmentsView.vue 对齐"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.landlord_a_token}')
        response = self.client.get(self.url)
        data = response.json()['data']
        item = data['items'][0]
        expected_fields = {
            'id', 'apartment_id', 'apartment_name',
            'type', 'type_display', 'status', 'status_display',
            'reject_reason', 'created_at', 'updated_at',
        }
        self.assertTrue(expected_fields.issubset(set(item.keys())))

    def test_list_reject_reason_for_rejected(self):
        """已驳回记录包含 reject_reason"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.landlord_a_token}')
        response = self.client.get(self.url)
        data = response.json()['data']
        rejected_item = next(item for item in data['items'] if item['status'] == 'rejected')
        self.assertEqual(rejected_item['reject_reason'], '名称不符合规范')


class AdminAuditListTests(TestCase):
    """管理员审核列表接口测试"""

    def setUp(self):
        self.client = APIClient()
        self.url = '/api/v1/admin/audits/'

        # 行政区与街道
        self.district = District.objects.create(name='浦东新区', level=1, code='310115', sort=0)
        self.street = District.objects.create(name='陆家嘴街道', level=2, code='310115001', parent=self.district, sort=0)

        # 商家
        self.landlord = User.objects.create(phone='13800138000', hashed_password='fake', role='landlord', is_active=True)

        # 管理员
        self.admin = User.objects.create(username='admin123', hashed_password='fake', role='admin', is_active=True)
        self.admin_token = self._get_token(self.admin)

        # 租客
        self.tenant = User.objects.create(phone='13900139000', hashed_password='fake', role='tenant', is_active=True)
        self.tenant_token = self._get_token(self.tenant)

        # 创建房源与审核单
        self.apartment = Apartment.objects.create(
            landlord=self.landlord,
            name='测试公寓',
            cover_image='https://example.com/cover.jpg',
            description='描述',
            district=self.district,
            street=self.street,
            detail_address='测试路1号',
            contact_phone='13800138000',
            status='pending_first_review',
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

        self.first_audit = AuditRecord.objects.create(
            apartment=self.apartment,
            type='first_review',
            status='pending',
            submitted_data={},
        )

        self.apartment2 = Apartment.objects.create(
            landlord=self.landlord,
            name='已上架公寓',
            cover_image='https://example.com/cover2.jpg',
            description='描述2',
            district=self.district,
            street=self.street,
            detail_address='测试路2号',
            contact_phone='13800138001',
            status='published',
        )
        self.change_audit = AuditRecord.objects.create(
            apartment=self.apartment2,
            type='change_review',
            status='pending',
            submitted_data={'name': '新名称'},
            original_data={'name': '已上架公寓'},
            changed_fields=['name'],
        )

    def _get_token(self, user):
        refresh = RefreshToken.for_user(user)
        refresh['role'] = user.role
        refresh['phone'] = user.phone
        refresh['username'] = user.username
        return str(refresh.access_token)

    def test_list_success(self):
        """管理员可查看审核列表"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        data = response.json()['data']
        self.assertEqual(data['total'], 2)

    def test_list_filter_by_type(self):
        """按 type 筛选"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        response = self.client.get(self.url, {'type': 'first_review'})
        data = response.json()['data']
        self.assertEqual(data['total'], 1)
        self.assertEqual(data['items'][0]['id'], self.first_audit.id)

    def test_list_filter_by_status(self):
        """按 status 筛选"""
        self.change_audit.status = 'approved'
        self.change_audit.save()
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        response = self.client.get(self.url, {'status': 'pending'})
        data = response.json()['data']
        self.assertEqual(data['total'], 1)
        self.assertEqual(data['items'][0]['id'], self.first_audit.id)

    def test_list_unauthorized(self):
        """未登录返回 401"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 401)

    def test_list_not_admin(self):
        """非管理员返回 403"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.tenant_token}')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    def test_list_order_by_created_at_desc(self):
        """列表按提交时间倒序"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        response = self.client.get(self.url)
        data = response.json()['data']
        items = data['items']
        # change_audit 后创建，created_at 更晚，应排在前面
        ids = [item['id'] for item in items]
        self.assertEqual(ids, sorted(ids, reverse=True))


class AdminAuditDetailTests(TestCase):
    """管理员审核详情接口测试"""

    def setUp(self):
        self.client = APIClient()

        self.district = District.objects.create(name='浦东新区', level=1, code='310115', sort=0)
        self.street = District.objects.create(name='陆家嘴街道', level=2, code='310115001', parent=self.district, sort=0)
        self.landlord = User.objects.create(phone='13800138000', hashed_password='fake', role='landlord', is_active=True)
        self.admin = User.objects.create(username='admin123', hashed_password='fake', role='admin', is_active=True)
        self.admin_token = self._get_token(self.admin)

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
        )
        self.change_audit = AuditRecord.objects.create(
            apartment=self.apartment,
            type='change_review',
            status='pending',
            submitted_data={'name': '新名称'},
            original_data={'name': '测试公寓'},
            changed_fields=['name'],
        )

    def _get_token(self, user):
        refresh = RefreshToken.for_user(user)
        refresh['role'] = user.role
        refresh['phone'] = user.phone
        refresh['username'] = user.username
        return str(refresh.access_token)

    def test_detail_success(self):
        """管理员可查看审核详情"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        response = self.client.get(f'/api/v1/admin/audits/{self.change_audit.id}/')
        self.assertEqual(response.status_code, 200)
        data = response.json()['data']
        self.assertEqual(data['id'], self.change_audit.id)
        self.assertEqual(data['type'], 'change_review')
        self.assertEqual(data['submitted_data'], {'name': '新名称'})
        self.assertEqual(data['original_data'], {'name': '测试公寓'})
        self.assertEqual(data['changed_fields'], ['name'])

    def test_detail_not_found(self):
        """审核单不存在返回 404"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        response = self.client.get('/api/v1/admin/audits/99999/')
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()['code'], 404001)


class AdminAuditApproveTests(TestCase):
    """管理员审核通过接口测试"""

    def setUp(self):
        self.client = APIClient()

        self.district = District.objects.create(name='浦东新区', level=1, code='310115', sort=0)
        self.street = District.objects.create(name='陆家嘴街道', level=2, code='310115001', parent=self.district, sort=0)
        self.landlord = User.objects.create(phone='13800138000', hashed_password='fake', role='landlord', is_active=True)
        self.admin = User.objects.create(username='admin123', hashed_password='fake', role='admin', is_active=True)
        self.admin_token = self._get_token(self.admin)

        self.apartment = Apartment.objects.create(
            landlord=self.landlord,
            name='测试公寓',
            cover_image='https://example.com/cover.jpg',
            description='描述',
            district=self.district,
            street=self.street,
            detail_address='测试路1号',
            contact_phone='13800138000',
            status='pending_first_review',
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

        self.first_audit = AuditRecord.objects.create(
            apartment=self.apartment,
            type='first_review',
            status='pending',
            submitted_data={},
        )

    def _get_token(self, user):
        refresh = RefreshToken.for_user(user)
        refresh['role'] = user.role
        refresh['phone'] = user.phone
        refresh['username'] = user.username
        return str(refresh.access_token)

    def test_approve_first_review(self):
        """首次审核通过：公寓置为 published"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        response = self.client.post(f'/api/v1/admin/audits/{self.first_audit.id}/approve/')
        self.assertEqual(response.status_code, 200)
        data = response.json()['data']
        self.assertEqual(data['action'], 'approve')
        self.assertEqual(data['status'], 'approved')

        self.apartment.refresh_from_db()
        self.assertEqual(self.apartment.status, 'published')

        self.first_audit.refresh_from_db()
        self.assertEqual(self.first_audit.status, 'approved')
        self.assertEqual(self.first_audit.reviewer_id, self.admin.id)

    def test_approve_already_processed(self):
        """已处理审核单再次通过返回 400"""
        self.first_audit.status = 'approved'
        self.first_audit.save()
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        response = self.client.post(f'/api/v1/admin/audits/{self.first_audit.id}/approve/')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['code'], 400002)

    def test_approve_change_review(self):
        """变更审核通过：快照覆盖原房源"""
        self.apartment.status = 'published'
        self.apartment.save()

        change_audit = AuditRecord.objects.create(
            apartment=self.apartment,
            type='change_review',
            status='pending',
            submitted_data={
                'name': '新名称',
                'cover_image': 'https://example.com/new.jpg',
                'description': '新描述',
                'district_id': self.district.id,
                'street_id': self.street.id,
                'detail_address': '新地址',
                'contact_phone': '13900139000',
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
            },
            original_data={},
            changed_fields=['name'],
        )

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        response = self.client.post(f'/api/v1/admin/audits/{change_audit.id}/approve/')
        self.assertEqual(response.status_code, 200)

        self.apartment.refresh_from_db()
        self.assertEqual(self.apartment.name, '新名称')
        self.assertEqual(self.apartment.cover_image, 'https://example.com/new.jpg')
        self.assertEqual(self.apartment.description, '新描述')
        self.assertEqual(self.apartment.detail_address, '新地址')
        self.assertEqual(self.apartment.contact_phone, '13900139000')
        self.assertEqual(self.apartment.min_monthly_rent, 3500)

        room_types = list(self.apartment.room_types.all())
        self.assertEqual(len(room_types), 1)
        self.assertEqual(room_types[0].name, '豪华单间')

        change_audit.refresh_from_db()
        self.assertEqual(change_audit.status, 'approved')
        self.assertEqual(change_audit.reviewer_id, self.admin.id)

    def test_approve_not_admin(self):
        """非管理员返回 403"""
        tenant = User.objects.create(phone='13900139000', hashed_password='fake', role='tenant', is_active=True)
        token = self._get_token(tenant)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        response = self.client.post(f'/api/v1/admin/audits/{self.first_audit.id}/approve/')
        self.assertEqual(response.status_code, 403)


class AdminAuditRejectTests(TestCase):
    """管理员审核驳回接口测试"""

    def setUp(self):
        self.client = APIClient()

        self.district = District.objects.create(name='浦东新区', level=1, code='310115', sort=0)
        self.street = District.objects.create(name='陆家嘴街道', level=2, code='310115001', parent=self.district, sort=0)
        self.landlord = User.objects.create(phone='13800138000', hashed_password='fake', role='landlord', is_active=True)
        self.admin = User.objects.create(username='admin123', hashed_password='fake', role='admin', is_active=True)
        self.admin_token = self._get_token(self.admin)

        self.apartment = Apartment.objects.create(
            landlord=self.landlord,
            name='测试公寓',
            cover_image='https://example.com/cover.jpg',
            description='描述',
            district=self.district,
            street=self.street,
            detail_address='测试路1号',
            contact_phone='13800138000',
            status='pending_first_review',
        )
        self.first_audit = AuditRecord.objects.create(
            apartment=self.apartment,
            type='first_review',
            status='pending',
            submitted_data={},
        )

    def _get_token(self, user):
        refresh = RefreshToken.for_user(user)
        refresh['role'] = user.role
        refresh['phone'] = user.phone
        refresh['username'] = user.username
        return str(refresh.access_token)

    def test_reject_first_review(self):
        """首次审核驳回：公寓置为 first_rejected，发送站内信"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        response = self.client.post(
            f'/api/v1/admin/audits/{self.first_audit.id}/reject/',
            {'reject_reason': '信息不完整，请补充房型照片'},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()['data']
        self.assertEqual(data['action'], 'reject')
        self.assertEqual(data['status'], 'rejected')

        self.apartment.refresh_from_db()
        self.assertEqual(self.apartment.status, 'first_rejected')

        self.first_audit.refresh_from_db()
        self.assertEqual(self.first_audit.status, 'rejected')
        self.assertEqual(self.first_audit.reject_reason, '信息不完整，请补充房型照片')
        self.assertEqual(self.first_audit.reviewer_id, self.admin.id)

        # 站内信
        msg = Message.objects.filter(user=self.landlord, related_apartment=self.apartment).first()
        self.assertIsNotNone(msg)
        self.assertEqual(msg.type, 'first_rejected')
        self.assertIn('信息不完整', msg.content)
        self.assertEqual(msg.related_audit_id, self.first_audit.id)
        self.assertEqual(msg.is_read, False)

    def test_reject_change_review(self):
        """变更审核驳回：原房源保持 published"""
        self.apartment.status = 'published'
        self.apartment.save()

        change_audit = AuditRecord.objects.create(
            apartment=self.apartment,
            type='change_review',
            status='pending',
            submitted_data={'name': '新名称'},
            original_data={'name': '测试公寓'},
            changed_fields=['name'],
        )

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        response = self.client.post(
            f'/api/v1/admin/audits/{change_audit.id}/reject/',
            {'reject_reason': '名称不符合规范'},
            format='json',
        )
        self.assertEqual(response.status_code, 200)

        self.apartment.refresh_from_db()
        self.assertEqual(self.apartment.status, 'published')
        self.assertEqual(self.apartment.name, '测试公寓')

        change_audit.refresh_from_db()
        self.assertEqual(change_audit.status, 'rejected')

        # 站内信
        msg = Message.objects.filter(user=self.landlord, related_audit=change_audit).first()
        self.assertIsNotNone(msg)
        self.assertEqual(msg.type, 'change_rejected')

    def test_reject_without_reason(self):
        """驳回未填原因返回 400"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        response = self.client.post(
            f'/api/v1/admin/audits/{self.first_audit.id}/reject/',
            {'reject_reason': ''},
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['code'], 400002)

    def test_reject_already_processed(self):
        """已处理审核单再次驳回返回 400"""
        self.first_audit.status = 'rejected'
        self.first_audit.save()
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        response = self.client.post(
            f'/api/v1/admin/audits/{self.first_audit.id}/reject/',
            {'reject_reason': '原因'},
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['code'], 400002)

    def test_reject_not_admin(self):
        """非管理员返回 403"""
        tenant = User.objects.create(phone='13900139000', hashed_password='fake', role='tenant', is_active=True)
        token = self._get_token(tenant)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        response = self.client.post(
            f'/api/v1/admin/audits/{self.first_audit.id}/reject/',
            {'reject_reason': '原因'},
            format='json',
        )
        self.assertEqual(response.status_code, 403)

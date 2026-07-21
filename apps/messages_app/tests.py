"""
消息模块单元测试
覆盖：站内信列表、标记已读、未读数、审核驳回触发站内信
"""
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.users.models import User
from apps.districts.models import District
from apps.apartments.models import Apartment
from apps.audits.models import AuditRecord
from apps.messages_app.models import Message


class MessageListTests(TestCase):
    """站内信列表接口测试"""

    def setUp(self):
        self.client = APIClient()
        self.url = '/api/v1/messages/'

        self.district = District.objects.create(name='浦东新区', level=1, code='310115', sort=0)
        self.street = District.objects.create(name='陆家嘴街道', level=2, code='310115001', parent=self.district, sort=0)
        self.landlord = User.objects.create(phone='13800138000', password="fake", role='landlord', is_active=True)
        self.token = self._get_token(self.landlord)

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
        self.audit = AuditRecord.objects.create(
            apartment=self.apartment,
            type='first_review',
            status='pending',
            submitted_data={},
        )

        # 创建 3 条消息，2 条未读 1 条已读
        self.msg1 = Message.objects.create(
            user=self.landlord, type='first_rejected', title='驳回1',
            content='原因1', related_apartment=self.apartment,
            related_audit=self.audit, is_read=False,
        )
        self.msg2 = Message.objects.create(
            user=self.landlord, type='change_rejected', title='驳回2',
            content='原因2', related_apartment=self.apartment,
            related_audit=self.audit, is_read=False,
        )
        self.msg3 = Message.objects.create(
            user=self.landlord, type='first_rejected', title='驳回3',
            content='原因3', related_apartment=self.apartment,
            related_audit=self.audit, is_read=True,
        )

    def _get_token(self, user):
        refresh = RefreshToken.for_user(user)
        refresh['role'] = user.role
        refresh['phone'] = user.phone
        refresh['username'] = user.username
        return str(refresh.access_token)

    def test_list_success(self):
        """登录用户可查看自己的站内信列表"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        data = response.json()['data']
        self.assertEqual(data['total'], 3)
        # 按 created_at 倒序（ID 不一定反映时间，但测试数据连续创建时 ID 递增）
        ids = [item['id'] for item in data['items']]
        self.assertEqual(ids, sorted(ids, reverse=True))

    def test_list_fields(self):
        """列表项包含所需字段"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')
        response = self.client.get(self.url)
        data = response.json()['data']['items'][0]
        self.assertIn('id', data)
        self.assertIn('type', data)
        self.assertIn('type_display', data)
        self.assertIn('title', data)
        self.assertIn('content', data)
        self.assertIn('related_apartment_id', data)
        self.assertIn('related_audit_id', data)
        self.assertIn('is_read', data)
        self.assertIn('created_at', data)
        self.assertEqual(data['related_apartment_id'], self.apartment.id)

    def test_list_unauthorized(self):
        """未登录返回 401"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 401)

    def test_list_only_own_messages(self):
        """只能查看自己的消息"""
        other = User.objects.create(phone='13900139000', password="fake", role='tenant', is_active=True)
        other_token = self._get_token(other)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {other_token}')
        response = self.client.get(self.url)
        data = response.json()['data']
        self.assertEqual(data['total'], 0)


class MessageReadTests(TestCase):
    """标记已读接口测试"""

    def setUp(self):
        self.client = APIClient()
        self.district = District.objects.create(name='浦东新区', level=1, code='310115', sort=0)
        self.street = District.objects.create(name='陆家嘴街道', level=2, code='310115001', parent=self.district, sort=0)
        self.landlord = User.objects.create(phone='13800138000', password="fake", role='landlord', is_active=True)
        self.token = self._get_token(self.landlord)
        self.apartment = Apartment.objects.create(
            landlord=self.landlord, name='测试公寓', cover_image='https://example.com/cover.jpg',
            description='描述', district=self.district, street=self.street,
            detail_address='测试路1号', contact_phone='13800138000', status='pending_first_review',
        )
        self.audit = AuditRecord.objects.create(apartment=self.apartment, type='first_review', status='pending', submitted_data={})
        self.msg = Message.objects.create(
            user=self.landlord, type='first_rejected', title='驳回',
            content='原因', related_apartment=self.apartment,
            related_audit=self.audit, is_read=False,
        )

    def _get_token(self, user):
        refresh = RefreshToken.for_user(user)
        refresh['role'] = user.role
        refresh['phone'] = user.phone
        refresh['username'] = user.username
        return str(refresh.access_token)

    def test_read_success(self):
        """标记已读成功"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')
        response = self.client.post(f'/api/v1/messages/{self.msg.id}/read/')
        self.assertEqual(response.status_code, 200)
        data = response.json()['data']
        self.assertEqual(data['id'], self.msg.id)
        self.assertEqual(data['is_read'], True)

        self.msg.refresh_from_db()
        self.assertTrue(self.msg.is_read)

    def test_read_not_found(self):
        """标记不存在的消息返回 404"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')
        response = self.client.post('/api/v1/messages/99999/read/')
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()['code'], 404001)

    def test_read_other_user_message(self):
        """不能标记其他用户的消息"""
        other = User.objects.create(phone='13900139000', password="fake", role='tenant', is_active=True)
        other_token = self._get_token(other)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {other_token}')
        response = self.client.post(f'/api/v1/messages/{self.msg.id}/read/')
        self.assertEqual(response.status_code, 404)

    def test_read_unauthorized(self):
        """未登录返回 401"""
        response = self.client.post(f'/api/v1/messages/{self.msg.id}/read/')
        self.assertEqual(response.status_code, 401)

    def test_read_idempotent(self):
        """重复标记已读不报错"""
        self.msg.is_read = True
        self.msg.save()
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')
        response = self.client.post(f'/api/v1/messages/{self.msg.id}/read/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['data']['is_read'], True)


class MessageUnreadCountTests(TestCase):
    """未读数接口测试"""

    def setUp(self):
        self.client = APIClient()
        self.district = District.objects.create(name='浦东新区', level=1, code='310115', sort=0)
        self.street = District.objects.create(name='陆家嘴街道', level=2, code='310115001', parent=self.district, sort=0)
        self.landlord = User.objects.create(phone='13800138000', password="fake", role='landlord', is_active=True)
        self.token = self._get_token(self.landlord)
        self.apartment = Apartment.objects.create(
            landlord=self.landlord, name='测试公寓', cover_image='https://example.com/cover.jpg',
            description='描述', district=self.district, street=self.street,
            detail_address='测试路1号', contact_phone='13800138000', status='pending_first_review',
        )
        self.audit = AuditRecord.objects.create(apartment=self.apartment, type='first_review', status='pending', submitted_data={})

        Message.objects.create(user=self.landlord, type='first_rejected', title='1', content='1',
                               related_apartment=self.apartment, related_audit=self.audit, is_read=False)
        Message.objects.create(user=self.landlord, type='first_rejected', title='2', content='2',
                               related_apartment=self.apartment, related_audit=self.audit, is_read=False)
        Message.objects.create(user=self.landlord, type='first_rejected', title='3', content='3',
                               related_apartment=self.apartment, related_audit=self.audit, is_read=True)

    def _get_token(self, user):
        refresh = RefreshToken.for_user(user)
        refresh['role'] = user.role
        refresh['phone'] = user.phone
        refresh['username'] = user.username
        return str(refresh.access_token)

    def test_unread_count_success(self):
        """未读数正确"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')
        response = self.client.get('/api/v1/messages/unread-count/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['data']['unread_count'], 2)

    def test_unread_count_unauthorized(self):
        """未登录返回 401"""
        response = self.client.get('/api/v1/messages/unread-count/')
        self.assertEqual(response.status_code, 401)

    def test_unread_count_after_read(self):
        """标记已读后未读数减少"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')
        msg = Message.objects.filter(user=self.landlord, is_read=False).first()
        self.client.post(f'/api/v1/messages/{msg.id}/read/')

        response = self.client.get('/api/v1/messages/unread-count/')
        self.assertEqual(response.json()['data']['unread_count'], 1)


class RejectNotificationTests(TestCase):
    """审核驳回触发站内信与短信日志测试"""

    def setUp(self):
        self.client = APIClient()
        self.district = District.objects.create(name='浦东新区', level=1, code='310115', sort=0)
        self.street = District.objects.create(name='陆家嘴街道', level=2, code='310115001', parent=self.district, sort=0)
        self.landlord = User.objects.create(phone='13800138000', password="fake", role='landlord', is_active=True)
        self.admin = User.objects.create(username='admin123', password="fake", role='admin', is_active=True)
        self.admin_token = self._get_token(self.admin)

        self.apartment = Apartment.objects.create(
            landlord=self.landlord, name='测试公寓', cover_image='https://example.com/cover.jpg',
            description='描述', district=self.district, street=self.street,
            detail_address='测试路1号', contact_phone='13800138000', status='pending_first_review',
        )
        self.first_audit = AuditRecord.objects.create(
            apartment=self.apartment, type='first_review', status='pending', submitted_data={},
        )

    def _get_token(self, user):
        refresh = RefreshToken.for_user(user)
        refresh['role'] = user.role
        refresh['phone'] = user.phone
        refresh['username'] = user.username
        return str(refresh.access_token)

    def test_reject_first_review_creates_message(self):
        """首次审核驳回创建站内信"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        response = self.client.post(
            f'/api/v1/admin/audits/{self.first_audit.id}/reject/',
            {'reject_reason': '信息不完整'},
            format='json',
        )
        self.assertEqual(response.status_code, 200)

        msg = Message.objects.filter(user=self.landlord, related_apartment=self.apartment).first()
        self.assertIsNotNone(msg)
        self.assertEqual(msg.type, 'first_rejected')
        self.assertEqual(msg.is_read, False)
        self.assertEqual(msg.related_audit_id, self.first_audit.id)
        self.assertIn('信息不完整', msg.content)

    def test_reject_first_review_creates_sms_log(self):
        """首次审核驳回记录短信日志"""
        from apps.users.models import SmsLog
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        self.client.post(
            f'/api/v1/admin/audits/{self.first_audit.id}/reject/',
            {'reject_reason': '信息不完整'},
            format='json',
        )

        log = SmsLog.objects.filter(phone='13800138000', template_code='REJECT_NOTIFY').first()
        self.assertIsNotNone(log)
        self.assertEqual(log.status, 'mock')
        self.assertIn('mock_send_ok', log.response)
        self.assertIn('mock_send_ok', log.response)

    def test_reject_change_review_creates_message(self):
        """变更审核驳回创建站内信"""
        self.apartment.status = 'published'
        self.apartment.save()
        change_audit = AuditRecord.objects.create(
            apartment=self.apartment, type='change_review', status='pending',
            submitted_data={'name': '新名称'}, original_data={'name': '测试公寓'},
            changed_fields=['name'],
        )

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        response = self.client.post(
            f'/api/v1/admin/audits/{change_audit.id}/reject/',
            {'reject_reason': '名称不符合规范'},
            format='json',
        )
        self.assertEqual(response.status_code, 200)

        msg = Message.objects.filter(user=self.landlord, related_audit=change_audit).first()
        self.assertIsNotNone(msg)
        self.assertEqual(msg.type, 'change_rejected')
        self.assertEqual(msg.is_read, False)
        self.assertEqual(msg.related_apartment_id, self.apartment.id)

    def test_reject_change_review_creates_sms_log(self):
        """变更审核驳回记录短信日志"""
        from apps.users.models import SmsLog
        self.apartment.status = 'published'
        self.apartment.save()
        change_audit = AuditRecord.objects.create(
            apartment=self.apartment, type='change_review', status='pending',
            submitted_data={'name': '新名称'}, original_data={'name': '测试公寓'},
            changed_fields=['name'],
        )

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        self.client.post(
            f'/api/v1/admin/audits/{change_audit.id}/reject/',
            {'reject_reason': '名称不符合规范'},
            format='json',
        )

        log = SmsLog.objects.filter(phone='13800138000', template_code='REJECT_NOTIFY').first()
        self.assertIsNotNone(log)
        self.assertEqual(log.status, 'mock')

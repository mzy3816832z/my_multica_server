"""
短信验证码模块单元测试
"""
import pytest
from datetime import timedelta
from django.utils import timezone
from django.test import Client, override_settings
from apps.users.models import VerifyCode, SmsLog
from core.verify_code import (
    create_and_send_sms_code,
    verify_sms_code,
    SMS_COOLDOWN_SECONDS,
    SMS_HOURLY_LIMIT,
    SMS_CODE_VALID_MINUTES,
)
from core.exceptions import TooManyRequestsException


@pytest.mark.django_db
def test_generate_and_send_sms_code_success():
    """正常发送验证码"""
    result = create_and_send_sms_code('13800138000', 'register')
    assert 'expires_in' in result
    assert result['expires_in'] == SMS_CODE_VALID_MINUTES * 60

    # 数据库应存在记录
    record = VerifyCode.objects.filter(phone='13800138000', purpose='register').latest('created_at')
    assert record is not None
    assert len(record.code) == 6
    assert record.used is False

    # 短信日志应存在
    log = SmsLog.objects.filter(phone='13800138000').latest('created_at')
    assert log.status == 'mock'


@pytest.mark.django_db
def test_sms_rate_limit_same_purpose_cooldown():
    """同一手机号同一用途 1 分钟内限发 1 次"""
    create_and_send_sms_code('13800138001', 'register')
    with pytest.raises(TooManyRequestsException) as exc_info:
        create_and_send_sms_code('13800138001', 'register')
    assert '429001' in str(exc_info.value) or '频繁' in str(exc_info.value)


@pytest.mark.django_db
def test_sms_rate_limit_different_purpose_allowed():
    """同一手机号不同用途 1 分钟内可发（跨 purpose 不受 1 分钟限制）"""
    create_and_send_sms_code('13800138002', 'register')
    result = create_and_send_sms_code('13800138002', 'login')
    assert result['expires_in'] == 300


@pytest.mark.django_db
def test_sms_rate_limit_hourly_limit():
    """同一手机号 1 小时内限发 10 次"""
    for i in range(SMS_HOURLY_LIMIT):
        create_and_send_sms_code('13800138003', 'register')
        # 绕过 1 分钟冷却：修改最新记录的 created_at 为更早时间
        latest = VerifyCode.objects.filter(phone='13800138003').latest('created_at')
        latest.created_at = timezone.now() - timedelta(seconds=SMS_COOLDOWN_SECONDS + 1)
        latest.save(update_fields=['created_at'])

    with pytest.raises(TooManyRequestsException) as exc_info:
        create_and_send_sms_code('13800138003', 'login')
    assert '429001' in str(exc_info.value) or '上限' in str(exc_info.value)


@pytest.mark.django_db
def test_verify_sms_code_success():
    """验证码校验成功并标记已使用"""
    create_and_send_sms_code('13800138004', 'register')
    record = VerifyCode.objects.filter(phone='13800138004', purpose='register').latest('created_at')

    ok = verify_sms_code('13800138004', 'register', record.code, mark_used=True)
    assert ok is True

    record.refresh_from_db()
    assert record.used is True


@pytest.mark.django_db
def test_verify_sms_code_wrong_code():
    """验证码错误应失败"""
    create_and_send_sms_code('13800138005', 'register')
    ok = verify_sms_code('13800138005', 'register', '000000', mark_used=False)
    assert ok is False


@pytest.mark.django_db
def test_verify_sms_code_used_code():
    """已使用的验证码应失败"""
    create_and_send_sms_code('13800138006', 'register')
    record = VerifyCode.objects.filter(phone='13800138006', purpose='register').latest('created_at')

    verify_sms_code('13800138006', 'register', record.code, mark_used=True)
    ok = verify_sms_code('13800138006', 'register', record.code, mark_used=False)
    assert ok is False


@pytest.mark.django_db
def test_verify_sms_code_expired():
    """过期的验证码应失败"""
    VerifyCode.objects.create(
        phone='13800138007',
        purpose='register',
        code='123456',
        used=False,
        expired_at=timezone.now() - timedelta(minutes=1),
    )
    ok = verify_sms_code('13800138007', 'register', '123456', mark_used=False)
    assert ok is False


@pytest.mark.django_db
def test_api_send_sms_code_success():
    """接口：正常发送验证码"""
    with override_settings(ALLOWED_HOSTS=['testserver']):
        c = Client()
        resp = c.post('/api/v1/auth/sms-code', {
            'phone': '13800138008',
            'purpose': 'register',
        }, content_type='application/json')
        assert resp.status_code == 200
        data = resp.json()
        assert data['code'] == 0
        assert data['data']['expires_in'] == 300


@pytest.mark.django_db
def test_api_send_sms_code_rate_limit():
    """接口：超频返回 429001"""
    with override_settings(ALLOWED_HOSTS=['testserver']):
        c = Client()
        resp = c.post('/api/v1/auth/sms-code', {
            'phone': '13800138009',
            'purpose': 'register',
        }, content_type='application/json')
        assert resp.status_code == 200

        resp2 = c.post('/api/v1/auth/sms-code', {
            'phone': '13800138009',
            'purpose': 'register',
        }, content_type='application/json')
        assert resp2.status_code == 429
        data = resp2.json()
        assert data['code'] == 429001


@pytest.mark.django_db
def test_api_send_sms_code_invalid_phone():
    """接口：手机号格式错误返回 400001"""
    with override_settings(ALLOWED_HOSTS=['testserver']):
        c = Client()
        resp = c.post('/api/v1/auth/sms-code', {
            'phone': '1380013800a',
            'purpose': 'register',
        }, content_type='application/json')
        assert resp.status_code == 400
        data = resp.json()
        assert data['code'] == 400001


@pytest.mark.django_db
def test_api_send_sms_code_invalid_purpose():
    """接口：purpose 不合法返回 400001"""
    with override_settings(ALLOWED_HOSTS=['testserver']):
        c = Client()
        resp = c.post('/api/v1/auth/sms-code', {
            'phone': '13800138010',
            'purpose': 'invalid_purpose',
        }, content_type='application/json')
        assert resp.status_code == 400
        data = resp.json()
        assert data['code'] == 400001

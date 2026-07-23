"""
用户认证模块单元测试
覆盖：注册、手机号+密码登录、手机号+验证码登录、首次登录身份选择、
      忘记密码、修改密码、管理员登录、获取当前用户
"""
import pytest
from datetime import timedelta
from django.utils import timezone
from django.test import Client, override_settings
from apps.users.models import User, VerifyCode
from core.verify_code import create_and_send_sms_code


# ---------- 工具函数 ----------

def _create_verify_code(phone, purpose):
    """创建并返回验证码字符串"""
    result = create_and_send_sms_code(phone, purpose)
    # 绕过频控：修改最新记录的 created_at
    latest = VerifyCode.objects.filter(phone=phone).latest('created_at')
    latest.created_at = timezone.now() - timedelta(seconds=70)
    latest.save(update_fields=['created_at'])
    return result['code']


def _register_user(client, phone, password, sms_code):
    """注册用户，返回响应"""
    return client.post('/api/v1/auth/register', {
        'phone': phone,
        'sms_code': sms_code,
        'password': password,
    }, content_type='application/json')


def _login_by_password(client, username, password):
    """用户名+密码登录，返回响应"""
    return client.post('/api/v1/auth/login-by-password', {
        'username': username,
        'password': password,
    }, content_type='application/json')


def _login_by_code(client, phone, sms_code):
    """验证码登录，返回响应"""
    return client.post('/api/v1/auth/login-by-code', {
        'phone': phone,
        'sms_code': sms_code,
    }, content_type='application/json')


# ---------- 注册 ----------

@pytest.mark.django_db
def test_register_success():
    """正常注册成功，role 为空"""
    with override_settings(ALLOWED_HOSTS=['testserver']):
        c = Client()
        code = _create_verify_code('13800138000', 'register')
        resp = _register_user(c, '13800138000', 'password123', code)
        assert resp.status_code == 200
        data = resp.json()
        assert data['code'] == 0
        assert 'access_token' in data['data']
        assert 'refresh_token' in data['data']
        assert data['data']['user']['role'] == ''
        assert data['data']['user']['phone'] == '13800138000'


@pytest.mark.django_db
def test_register_invalid_sms_code():
    """注册时验证码错误"""
    with override_settings(ALLOWED_HOSTS=['testserver']):
        c = Client()
        # 不创建验证码，直接提交错误验证码
        resp = _register_user(c, '13800138001', 'password123', '000000')
        assert resp.status_code == 200
        data = resp.json()
        assert data['code'] == 400002


@pytest.mark.django_db
def test_register_duplicate_phone():
    """重复手机号注册"""
    with override_settings(ALLOWED_HOSTS=['testserver']):
        c = Client()
        code = _create_verify_code('13800138002', 'register')
        _register_user(c, '13800138002', 'password123', code)

        code2 = _create_verify_code('13800138002', 'register')
        resp = _register_user(c, '13800138002', 'password123', code2)
        assert resp.status_code == 200
        data = resp.json()
        assert data['code'] == 409001


# ---------- 手机号+密码登录 ----------

@pytest.mark.django_db
def test_login_by_password_success():
    """密码登录成功"""
    with override_settings(ALLOWED_HOSTS=['testserver']):
        c = Client()
        code = _create_verify_code('13800138010', 'register')
        _register_user(c, '13800138010', 'password123', code)

        resp = _login_by_password(c, '13800138010', 'password123')
        assert resp.status_code == 200
        data = resp.json()
        assert data['code'] == 0
        assert 'access_token' in data['data']
        assert data['data']['user']['phone'] == '13800138010'


@pytest.mark.django_db
def test_login_by_password_wrong_password():
    """密码错误返回明确错误码"""
    with override_settings(ALLOWED_HOSTS=['testserver']):
        c = Client()
        code = _create_verify_code('13800138011', 'register')
        _register_user(c, '13800138011', 'password123', code)

        resp = _login_by_password(c, '13800138011', 'wrongpassword')
        assert resp.status_code == 200
        data = resp.json()
        assert data['code'] == 400002


@pytest.mark.django_db
def test_login_by_password_user_not_found():
    """登录不存在的用户"""
    with override_settings(ALLOWED_HOSTS=['testserver']):
        c = Client()
        resp = _login_by_password(c, '13800138012', 'password123')
        assert resp.status_code == 200
        data = resp.json()
        assert data['code'] == 404001


# ---------- 手机号+验证码登录 ----------

@pytest.mark.django_db
def test_login_by_code_success():
    """验证码登录成功"""
    with override_settings(ALLOWED_HOSTS=['testserver']):
        c = Client()
        code = _create_verify_code('13800138020', 'register')
        _register_user(c, '13800138020', 'password123', code)

        login_code = _create_verify_code('13800138020', 'login')
        resp = _login_by_code(c, '13800138020', login_code)
        assert resp.status_code == 200
        data = resp.json()
        assert data['code'] == 0
        assert 'access_token' in data['data']


@pytest.mark.django_db
def test_login_by_code_wrong_code():
    """验证码错误返回明确错误码"""
    with override_settings(ALLOWED_HOSTS=['testserver']):
        c = Client()
        code = _create_verify_code('13800138021', 'register')
        _register_user(c, '13800138021', 'password123', code)

        resp = _login_by_code(c, '13800138021', '000000')
        assert resp.status_code == 200
        data = resp.json()
        assert data['code'] == 400002


# ---------- 首次登录身份选择 ----------

@pytest.mark.django_db
def test_select_role_success():
    """首次登录选择身份成功"""
    with override_settings(ALLOWED_HOSTS=['testserver']):
        c = Client()
        code = _create_verify_code('13800138030', 'register')
        reg_resp = _register_user(c, '13800138030', 'password123', code)
        token = reg_resp.json()['data']['access_token']

        resp = c.post('/api/v1/auth/select-role', {
            'role': 'tenant',
        }, content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {token}')
        assert resp.status_code == 200
        data = resp.json()
        assert data['code'] == 0
        assert data['data']['role'] == 'tenant'


@pytest.mark.django_db
def test_select_role_repeat():
    """已选择身份后不可重复选择"""
    with override_settings(ALLOWED_HOSTS=['testserver']):
        c = Client()
        code = _create_verify_code('13800138031', 'register')
        reg_resp = _register_user(c, '13800138031', 'password123', code)
        token = reg_resp.json()['data']['access_token']

        c.post('/api/v1/auth/select-role', {
            'role': 'landlord',
        }, content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {token}')

        resp = c.post('/api/v1/auth/select-role', {
            'role': 'tenant',
        }, content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {token}')
        assert resp.status_code == 200
        data = resp.json()
        assert data['code'] == 400002


@pytest.mark.django_db
def test_select_role_invalid_role():
    """选择非法身份"""
    with override_settings(ALLOWED_HOSTS=['testserver']):
        c = Client()
        code = _create_verify_code('13800138032', 'register')
        reg_resp = _register_user(c, '13800138032', 'password123', code)
        token = reg_resp.json()['data']['access_token']

        resp = c.post('/api/v1/auth/select-role', {
            'role': 'admin',
        }, content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {token}')
        assert resp.status_code == 200
        data = resp.json()
        assert data['code'] == 400001


# ---------- 忘记密码 ----------

@pytest.mark.django_db
def test_reset_password_success():
    """忘记密码重置成功"""
    with override_settings(ALLOWED_HOSTS=['testserver']):
        c = Client()
        code = _create_verify_code('13800138040', 'register')
        _register_user(c, '13800138040', 'password123', code)

        reset_code = _create_verify_code('13800138040', 'reset_password')
        resp = c.post('/api/v1/auth/reset-password', {
            'phone': '13800138040',
            'sms_code': reset_code,
            'new_password': 'newpassword456',
        }, content_type='application/json')
        assert resp.status_code == 200
        data = resp.json()
        assert data['code'] == 0
        assert data['data']['success'] is True

        # 用新密码登录
        login_resp = _login_by_password(c, '13800138040', 'newpassword456')
        assert login_resp.status_code == 200


@pytest.mark.django_db
def test_reset_password_invalid_code():
    """忘记密码验证码错误"""
    with override_settings(ALLOWED_HOSTS=['testserver']):
        c = Client()
        code = _create_verify_code('13800138041', 'register')
        _register_user(c, '13800138041', 'password123', code)

        resp = c.post('/api/v1/auth/reset-password', {
            'phone': '13800138041',
            'sms_code': '000000',
            'new_password': 'newpassword456',
        }, content_type='application/json')
        assert resp.status_code == 200
        data = resp.json()
        assert data['code'] == 400002


# ---------- 修改密码 ----------

@pytest.mark.django_db
def test_change_password_success():
    """登录用户修改密码成功"""
    with override_settings(ALLOWED_HOSTS=['testserver']):
        c = Client()
        code = _create_verify_code('13800138050', 'register')
        reg_resp = _register_user(c, '13800138050', 'password123', code)
        token = reg_resp.json()['data']['access_token']

        change_code = _create_verify_code('13800138050', 'change_password')
        resp = c.post('/api/v1/auth/change-password', {
            'sms_code': change_code,
            'new_password': 'newpassword789',
        }, content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {token}')
        assert resp.status_code == 200
        data = resp.json()
        assert data['code'] == 0
        assert data['data']['success'] is True

        # 用新密码登录
        login_resp = _login_by_password(c, '13800138050', 'newpassword789')
        assert login_resp.status_code == 200


@pytest.mark.django_db
def test_change_password_invalid_code():
    """修改密码验证码错误"""
    with override_settings(ALLOWED_HOSTS=['testserver']):
        c = Client()
        code = _create_verify_code('13800138051', 'register')
        reg_resp = _register_user(c, '13800138051', 'password123', code)
        token = reg_resp.json()['data']['access_token']

        resp = c.post('/api/v1/auth/change-password', {
            'sms_code': '000000',
            'new_password': 'newpassword789',
        }, content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {token}')
        assert resp.status_code == 200
        data = resp.json()
        assert data['code'] == 400002


# ---------- 管理员登录（统一使用 login-by-password） ----------

def _create_admin_user():
    """创建管理员用户用于测试"""
    user = User.objects.create(
        username='admin123',
        role='admin',
        is_active=True,
    )
    user.set_password('3816832z')
    user.save(update_fields=['password', 'updated_at'])
    return user


@pytest.mark.django_db
def test_admin_login_success():
    """管理员通过 login-by-password 登录成功"""
    _create_admin_user()
    with override_settings(ALLOWED_HOSTS=['testserver']):
        c = Client()
        resp = _login_by_password(c, 'admin123', '3816832z')
        assert resp.status_code == 200
        data = resp.json()
        assert data['code'] == 0
        assert 'access_token' in data['data']
        assert data['data']['user']['role'] == 'admin'
        assert data['data']['user']['username'] == 'admin123'


@pytest.mark.django_db
def test_admin_login_wrong_password():
    """管理员通过 login-by-password 密码错误"""
    _create_admin_user()
    with override_settings(ALLOWED_HOSTS=['testserver']):
        c = Client()
        resp = _login_by_password(c, 'admin123', 'wrongpassword')
        assert resp.status_code == 200
        data = resp.json()
        assert data['code'] == 400002


# ---------- 获取当前用户 ----------

@pytest.mark.django_db
def test_me_success():
    """获取当前登录用户成功"""
    with override_settings(ALLOWED_HOSTS=['testserver']):
        c = Client()
        code = _create_verify_code('13800138070', 'register')
        reg_resp = _register_user(c, '13800138070', 'password123', code)
        token = reg_resp.json()['data']['access_token']

        resp = c.get('/api/v1/auth/me', HTTP_AUTHORIZATION=f'Bearer {token}')
        assert resp.status_code == 200
        data = resp.json()
        assert data['code'] == 0
        assert data['data']['phone'] == '13800138070'


@pytest.mark.django_db
def test_me_unauthorized():
    """未登录访问 me 返回 401"""
    with override_settings(ALLOWED_HOSTS=['testserver']):
        c = Client()
        resp = c.get('/api/v1/auth/me')
        assert resp.status_code == 401
        data = resp.json()
        assert data['code'] == 401001

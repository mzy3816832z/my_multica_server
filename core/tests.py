"""
权限隔离单元测试
覆盖：角色权限类 IsTenant、IsLandlord、IsAdmin 的校验逻辑，
以及通过 DRF 异常处理返回 403001 的统一响应格式。
"""
import pytest
import bcrypt
from rest_framework.test import APIRequestFactory
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.exceptions import PermissionDenied

from core.permissions import IsTenant, IsLandlord, IsAdmin
from core.exceptions import custom_exception_handler
from apps.users.models import User


# ---------- 工具函数 ----------

def _create_user(phone, role, password='password123'):
    """创建测试用户并返回"""
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    if role == 'admin':
        return User.objects.create(
            username='admin_test',
            role='admin',
            hashed_password=hashed,
            is_active=True,
        )
    return User.objects.create(
        phone=phone,
        role=role,
        hashed_password=hashed,
        is_active=True,
    )


def _get_token(user):
    """获取用户的 JWT access token"""
    return str(RefreshToken.for_user(user).access_token)


def _check_permission(user, perm_class):
    """使用 JWTAuthentication 鉴权后检查权限类"""
    factory = APIRequestFactory()
    request = factory.get('/test')
    token = _get_token(user)
    request.META['HTTP_AUTHORIZATION'] = f'Bearer {token}'
    auth = JWTAuthentication()
    request.user, _ = auth.authenticate(request)
    perm = perm_class()
    return perm.has_permission(request, None)


# ---------- IsTenant ----------

@pytest.mark.django_db
def test_is_tenant_true():
    """租客用户通过 IsTenant 校验"""
    user = _create_user('13800138100', 'tenant')
    assert _check_permission(user, IsTenant) is True


@pytest.mark.django_db
def test_is_tenant_false_for_landlord():
    """商家用户被 IsTenant 拒绝"""
    user = _create_user('13800138101', 'landlord')
    assert _check_permission(user, IsTenant) is False


@pytest.mark.django_db
def test_is_tenant_false_for_admin():
    """管理员被 IsTenant 拒绝"""
    user = _create_user(None, 'admin')
    assert _check_permission(user, IsTenant) is False


# ---------- IsLandlord ----------

@pytest.mark.django_db
def test_is_landlord_true():
    """商家用户通过 IsLandlord 校验"""
    user = _create_user('13800138102', 'landlord')
    assert _check_permission(user, IsLandlord) is True


@pytest.mark.django_db
def test_is_landlord_false_for_tenant():
    """租客用户被 IsLandlord 拒绝"""
    user = _create_user('13800138103', 'tenant')
    assert _check_permission(user, IsLandlord) is False


@pytest.mark.django_db
def test_is_landlord_false_for_admin():
    """管理员被 IsLandlord 拒绝"""
    user = _create_user(None, 'admin')
    assert _check_permission(user, IsLandlord) is False


# ---------- IsAdmin ----------

@pytest.mark.django_db
def test_is_admin_true():
    """管理员通过 IsAdmin 校验"""
    user = _create_user(None, 'admin')
    assert _check_permission(user, IsAdmin) is True


@pytest.mark.django_db
def test_is_admin_false_for_tenant():
    """租客被 IsAdmin 拒绝"""
    user = _create_user('13800138104', 'tenant')
    assert _check_permission(user, IsAdmin) is False


@pytest.mark.django_db
def test_is_admin_false_for_landlord():
    """商家被 IsAdmin 拒绝"""
    user = _create_user('13800138105', 'landlord')
    assert _check_permission(user, IsAdmin) is False


# ---------- 403001 统一响应格式 ----------

@pytest.mark.django_db
def test_permission_denied_returns_403001():
    """权限不足时通过 DRF 异常处理返回 403001"""
    factory = APIRequestFactory()
    tenant = _create_user('13800138106', 'tenant')
    token = _get_token(tenant)
    request = factory.get('/test')
    request.META['HTTP_AUTHORIZATION'] = f'Bearer {token}'
    auth = JWTAuthentication()
    request.user, _ = auth.authenticate(request)

    perm = IsLandlord()
    assert perm.has_permission(request, None) is False

    try:
        raise PermissionDenied(detail='仅商家可访问')
    except PermissionDenied as exc:
        response = custom_exception_handler(exc, {'request': request, 'view': None})
        assert response.status_code == 403
        data = response.data
        assert data['code'] == 403001
        assert data['message'] == '仅商家可访问'
        assert data['data'] == {}


@pytest.mark.django_db
def test_admin_permission_denied_returns_403001():
    """非管理员访问管理员接口返回 403001"""
    factory = APIRequestFactory()
    landlord = _create_user('13800138107', 'landlord')
    token = _get_token(landlord)
    request = factory.get('/test')
    request.META['HTTP_AUTHORIZATION'] = f'Bearer {token}'
    auth = JWTAuthentication()
    request.user, _ = auth.authenticate(request)

    perm = IsAdmin()
    assert perm.has_permission(request, None) is False

    try:
        raise PermissionDenied(detail='仅管理员可访问')
    except PermissionDenied as exc:
        response = custom_exception_handler(exc, {'request': request, 'view': None})
        assert response.status_code == 403
        data = response.data
        assert data['code'] == 403001
        assert data['message'] == '仅管理员可访问'
        assert data['data'] == {}


@pytest.mark.django_db
def test_tenant_permission_denied_returns_403001():
    """非租客访问租客接口返回 403001"""
    factory = APIRequestFactory()
    admin = _create_user(None, 'admin')
    token = _get_token(admin)
    request = factory.get('/test')
    request.META['HTTP_AUTHORIZATION'] = f'Bearer {token}'
    auth = JWTAuthentication()
    request.user, _ = auth.authenticate(request)

    perm = IsTenant()
    assert perm.has_permission(request, None) is False

    try:
        raise PermissionDenied(detail='仅租客可访问')
    except PermissionDenied as exc:
        response = custom_exception_handler(exc, {'request': request, 'view': None})
        assert response.status_code == 403
        data = response.data
        assert data['code'] == 403001
        assert data['message'] == '仅租客可访问'
        assert data['data'] == {}

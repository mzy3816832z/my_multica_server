"""
核心模块单元测试
覆盖：统一响应体、错误码、权限类、异常处理
"""
from unittest.mock import MagicMock
from core.response import unified_response, ErrorCode, ERROR_MESSAGES
from core.exceptions import (
    BusinessException,
    ParamErrorException,
    ForbiddenException,
    NotFoundException,
    ConflictException,
    TooManyRequestsException,
)
from core.permissions import IsTenant, IsLandlord, IsAdmin


# ---------- 统一响应体 ----------

def test_error_code_values():
    """错误码常量值正确"""
    assert ErrorCode.SUCCESS == 0
    assert ErrorCode.PARAM_ERROR == 400001
    assert ErrorCode.BUSINESS_ERROR == 400002
    assert ErrorCode.UNAUTHORIZED == 401001
    assert ErrorCode.FORBIDDEN == 403001
    assert ErrorCode.NOT_FOUND == 404001
    assert ErrorCode.CONFLICT == 409001
    assert ErrorCode.TOO_MANY_REQUESTS == 429001
    assert ErrorCode.SERVER_ERROR == 500001


def test_error_messages_complete():
    """每个错误码都有对应的消息"""
    for code in [
        ErrorCode.SUCCESS,
        ErrorCode.PARAM_ERROR,
        ErrorCode.BUSINESS_ERROR,
        ErrorCode.UNAUTHORIZED,
        ErrorCode.FORBIDDEN,
        ErrorCode.NOT_FOUND,
        ErrorCode.CONFLICT,
        ErrorCode.TOO_MANY_REQUESTS,
        ErrorCode.SERVER_ERROR,
    ]:
        assert code in ERROR_MESSAGES


def test_unified_response_success():
    """成功响应格式正确"""
    resp = unified_response(data={'id': 1})
    assert resp.status_code == 200
    assert resp.data['code'] == ErrorCode.SUCCESS
    assert resp.data['message'] == ERROR_MESSAGES[ErrorCode.SUCCESS]
    assert resp.data['data'] == {'id': 1}


def test_unified_response_error():
    """错误响应格式正确"""
    resp = unified_response(
        code=ErrorCode.NOT_FOUND,
        message='自定义消息',
        status_code=404,
    )
    assert resp.status_code == 404
    assert resp.data['code'] == ErrorCode.NOT_FOUND
    assert resp.data['message'] == '自定义消息'
    assert resp.data['data'] == {}


def test_unified_response_no_data():
    """不传 data 时默认为空字典"""
    resp = unified_response()
    assert resp.data['data'] == {}
    assert resp.status_code == 200


def test_unified_response_default_message():
    """不传 message 时使用错误码默认消息"""
    resp = unified_response(code=ErrorCode.UNAUTHORIZED)
    assert resp.data['message'] == ERROR_MESSAGES[ErrorCode.UNAUTHORIZED]


# ---------- 业务异常 ----------

def test_business_exception():
    """BusinessException 携带错误码"""
    exc = BusinessException('测试错误', code=400002)
    assert str(exc) == '测试错误'
    assert exc.custom_code == 400002


def test_param_error_exception():
    """ParamErrorException 默认错误码 400001"""
    exc = ParamErrorException('参数错误')
    assert exc.custom_code == 400001


def test_forbidden_exception():
    """ForbiddenException 默认错误码 403001"""
    exc = ForbiddenException('无权限')
    assert exc.custom_code == 403001


def test_not_found_exception():
    """NotFoundException 默认错误码 404001"""
    exc = NotFoundException('资源不存在')
    assert exc.custom_code == 404001


def test_conflict_exception():
    """ConflictException 默认错误码 409001"""
    exc = ConflictException('资源冲突')
    assert exc.custom_code == 409001


def test_too_many_requests_exception():
    """TooManyRequestsException 默认错误码 429001"""
    exc = TooManyRequestsException('请求过于频繁')
    assert exc.custom_code == 429001


# ---------- 权限类 ----------

def _create_mock_request(role=None, is_authenticated=True):
    """创建模拟请求对象"""
    user = MagicMock()
    user.is_authenticated = is_authenticated
    user.role = role
    request = MagicMock()
    request.user = user
    return request


class TestIsTenant:
    def test_tenant_allowed(self):
        request = _create_mock_request(role='tenant')
        assert IsTenant().has_permission(request, None) is True

    def test_landlord_rejected(self):
        request = _create_mock_request(role='landlord')
        assert IsTenant().has_permission(request, None) is False

    def test_admin_rejected(self):
        request = _create_mock_request(role='admin')
        assert IsTenant().has_permission(request, None) is False

    def test_no_role_rejected(self):
        request = _create_mock_request(role='')
        assert IsTenant().has_permission(request, None) is False

    def test_unauthenticated_rejected(self):
        request = _create_mock_request(role='tenant', is_authenticated=False)
        assert IsTenant().has_permission(request, None) is False


class TestIsLandlord:
    def test_landlord_allowed(self):
        request = _create_mock_request(role='landlord')
        assert IsLandlord().has_permission(request, None) is True

    def test_tenant_rejected(self):
        request = _create_mock_request(role='tenant')
        assert IsLandlord().has_permission(request, None) is False

    def test_admin_rejected(self):
        request = _create_mock_request(role='admin')
        assert IsLandlord().has_permission(request, None) is False

    def test_unauthenticated_rejected(self):
        request = _create_mock_request(is_authenticated=False)
        assert IsLandlord().has_permission(request, None) is False


class TestIsAdmin:
    def test_admin_allowed(self):
        request = _create_mock_request(role='admin')
        assert IsAdmin().has_permission(request, None) is True

    def test_tenant_rejected(self):
        request = _create_mock_request(role='tenant')
        assert IsAdmin().has_permission(request, None) is False

    def test_landlord_rejected(self):
        request = _create_mock_request(role='landlord')
        assert IsAdmin().has_permission(request, None) is False

    def test_unauthenticated_rejected(self):
        request = _create_mock_request(is_authenticated=False)
        assert IsAdmin().has_permission(request, None) is False

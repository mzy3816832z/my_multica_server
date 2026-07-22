"""
业务异常与全局异常处理
"""
from rest_framework.views import exception_handler
from rest_framework.exceptions import (
    APIException,
    AuthenticationFailed,
    NotAuthenticated,
    PermissionDenied,
    NotFound,
    ValidationError,
    Throttled,
)
from django.core.exceptions import ObjectDoesNotExist
from .response import unified_response, ErrorCode


class BusinessException(APIException):
    """
    业务异常基类
    """
    status_code = 400
    default_code = ErrorCode.BUSINESS_ERROR
    default_detail = '业务规则校验失败'

    def __init__(self, detail=None, code=None):
        if detail is None:
            detail = self.default_detail
        if code is None:
            code = self.default_code
        self.custom_code = code
        super().__init__(detail=detail, code=code)


class ParamErrorException(BusinessException):
    status_code = 400
    default_code = ErrorCode.PARAM_ERROR
    default_detail = '参数校验失败'


class UnauthorizedException(BusinessException):
    status_code = 401
    default_code = ErrorCode.UNAUTHORIZED
    default_detail = '未登录或 Token 失效'


class ForbiddenException(BusinessException):
    status_code = 403
    default_code = ErrorCode.FORBIDDEN
    default_detail = '无权限访问'


class NotFoundException(BusinessException):
    status_code = 404
    default_code = ErrorCode.NOT_FOUND
    default_detail = '资源不存在'


class ConflictException(BusinessException):
    status_code = 409
    default_code = ErrorCode.CONFLICT
    default_detail = '资源冲突'


class TooManyRequestsException(BusinessException):
    status_code = 429
    default_code = ErrorCode.TOO_MANY_REQUESTS
    default_detail = '请求过于频繁'


class ServerErrorException(BusinessException):
    status_code = 500
    default_code = ErrorCode.SERVER_ERROR
    default_detail = '服务器内部错误'


def custom_exception_handler(exc, context):
    """
    自定义全局异常处理
    """
    # 先调用 DRF 默认异常处理
    response = exception_handler(exc, context)

    if response is not None:
        # DRF 已处理的异常，统一包装响应格式
        if isinstance(exc, ValidationError):
            code = ErrorCode.PARAM_ERROR
            message = '参数校验失败'
            if isinstance(exc.detail, dict):
                # 提取第一个错误信息
                first_errors = []
                for v in exc.detail.values():
                    if isinstance(v, list):
                        first_errors.append(str(v[0]))
                    else:
                        first_errors.append(str(v))
                if first_errors:
                    message = first_errors[0]
            elif isinstance(exc.detail, list):
                message = str(exc.detail[0])
            return unified_response(code=code, message=message, status_code=400)

        elif isinstance(exc, (AuthenticationFailed, NotAuthenticated)):
            return unified_response(code=ErrorCode.UNAUTHORIZED, message=str(exc.detail), status_code=401)

        elif isinstance(exc, PermissionDenied):
            return unified_response(code=ErrorCode.FORBIDDEN, message=str(exc.detail), status_code=403)

        elif isinstance(exc, NotFound):
            return unified_response(code=ErrorCode.NOT_FOUND, message=str(exc.detail), status_code=404)

        elif isinstance(exc, Throttled):
            return unified_response(code=ErrorCode.TOO_MANY_REQUESTS, message=str(exc.detail), status_code=429)

        elif isinstance(exc, BusinessException):
            code = getattr(exc, 'custom_code', ErrorCode.SERVER_ERROR)
            return unified_response(code=code, message=str(exc.detail), status_code=200)

        else:
            # 其他 DRF 异常
            code = getattr(exc, 'custom_code', ErrorCode.SERVER_ERROR)
            return unified_response(code=code, message=str(exc.detail), status_code=response.status_code)

    # DRF 未处理的异常（如 Django 原生异常）
    if isinstance(exc, ObjectDoesNotExist):
        return unified_response(code=ErrorCode.NOT_FOUND, message='资源不存在', status_code=404)

    # 未知异常，返回 500
    import logging
    logger = logging.getLogger('apps')
    logger.exception('Unhandled exception')
    return unified_response(code=ErrorCode.SERVER_ERROR, message='服务器内部错误', status_code=500)

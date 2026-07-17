"""
统一响应体与错误码
"""
from rest_framework.response import Response
from rest_framework import status


class ErrorCode:
    SUCCESS = 0
    PARAM_ERROR = 400001
    BUSINESS_ERROR = 400002
    UNAUTHORIZED = 401001
    FORBIDDEN = 403001
    NOT_FOUND = 404001
    CONFLICT = 409001
    TOO_MANY_REQUESTS = 429001
    SERVER_ERROR = 500001


ERROR_MESSAGES = {
    ErrorCode.SUCCESS: 'success',
    ErrorCode.PARAM_ERROR: '参数校验失败',
    ErrorCode.BUSINESS_ERROR: '业务规则校验失败',
    ErrorCode.UNAUTHORIZED: '未登录或 Token 失效',
    ErrorCode.FORBIDDEN: '无权限访问',
    ErrorCode.NOT_FOUND: '资源不存在',
    ErrorCode.CONFLICT: '资源冲突',
    ErrorCode.TOO_MANY_REQUESTS: '请求过于频繁',
    ErrorCode.SERVER_ERROR: '服务器内部错误',
}


def unified_response(data=None, code=ErrorCode.SUCCESS, message=None, status_code=status.HTTP_200_OK):
    """
    统一响应封装
    """
    if message is None:
        message = ERROR_MESSAGES.get(code, 'unknown error')
    return Response(
        {
            'code': code,
            'message': message,
            'data': data if data is not None else {},
        },
        status=status_code,
    )

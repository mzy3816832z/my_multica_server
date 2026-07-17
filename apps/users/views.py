"""
用户认证相关视图：短信验证码、注册、登录等
"""
import logging
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework import serializers
from drf_spectacular.utils import extend_schema
from core.response import unified_response, ErrorCode
from core.exceptions import ParamErrorException
from core.verify_code import create_and_send_sms_code

logger = logging.getLogger('apps')


class SmsCodeRequestSerializer(serializers.Serializer):
    """短信验证码请求序列化器"""
    phone = serializers.CharField(max_length=11, min_length=11, help_text='手机号，11位数字')
    purpose = serializers.ChoiceField(
        choices=['register', 'login', 'reset_password', 'change_password'],
        help_text='验证码用途',
    )


class SmsCodeResponseSerializer(serializers.Serializer):
    """短信验证码响应序列化器"""
    expires_in = serializers.IntegerField(help_text='有效期（秒）')


@extend_schema(
    request=SmsCodeRequestSerializer,
    responses={200: SmsCodeResponseSerializer},
    summary='发送短信验证码',
    description='发送短信验证码，含频控：1分钟限发1次，1小时限发10次。V1.0 为 mock 模式。',
    tags=['认证'],
)
@api_view(['POST'])
@permission_classes([AllowAny])
def send_sms_code(request):
    """
    POST /api/v1/auth/sms-code
    发送短信验证码
    """
    serializer = SmsCodeRequestSerializer(data=request.data)
    if not serializer.is_valid():
        raise ParamErrorException(serializer.errors)

    phone = serializer.validated_data['phone']
    purpose = serializer.validated_data['purpose']

    # 校验手机号格式（纯数字）
    if not phone.isdigit():
        raise ParamErrorException('手机号格式不正确')

    result = create_and_send_sms_code(phone, purpose)

    return unified_response(
        data={'expires_in': result['expires_in']},
        code=ErrorCode.SUCCESS,
    )

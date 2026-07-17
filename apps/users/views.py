"""
用户认证相关视图：注册、登录、身份选择、密码管理等
"""
import logging
import bcrypt
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import serializers
from drf_spectacular.utils import extend_schema
from rest_framework_simplejwt.tokens import RefreshToken

from core.response import unified_response, ErrorCode
from core.exceptions import ParamErrorException, BusinessException, UnauthorizedException
from core.verify_code import verify_sms_code
from core.permissions import IsTenant, IsLandlord, IsAdmin
from apps.users.models import User
from apps.users.serializers import (
    RegisterSerializer,
    LoginByPasswordSerializer,
    LoginByCodeSerializer,
    SelectRoleSerializer,
    ResetPasswordSerializer,
    ChangePasswordSerializer,
    AdminLoginSerializer,
    TokenResponseSerializer,
    UserSerializer,
)

logger = logging.getLogger('apps')


def _hash_password(password: str) -> str:
    """bcrypt 加密密码"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def _check_password(password: str, hashed: str) -> bool:
    """bcrypt 校验密码"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))


def _generate_tokens(user: User) -> dict:
    """生成 JWT Token 对"""
    refresh = RefreshToken.for_user(user)
    # 自定义 payload 中嵌入 role
    refresh['role'] = user.role
    refresh['phone'] = user.phone
    refresh['username'] = user.username
    return {
        'access_token': str(refresh.access_token),
        'refresh_token': str(refresh),
    }


def _user_to_dict(user: User) -> dict:
    """将 User 对象转为字典"""
    return {
        'id': user.id,
        'phone': user.phone,
        'username': user.username,
        'role': user.role,
        'is_active': user.is_active,
    }


@extend_schema(
    request=RegisterSerializer,
    responses={200: TokenResponseSerializer},
    summary='用户注册',
    description='手机号+验证码注册，注册成功后 role 为空，需前端跳转身份选择。',
    tags=['认证'],
)
@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """
    POST /api/v1/auth/register
    用户注册
    """
    serializer = RegisterSerializer(data=request.data)
    if not serializer.is_valid():
        raise ParamErrorException(serializer.errors)

    phone = serializer.validated_data['phone']
    sms_code = serializer.validated_data['sms_code']
    password = serializer.validated_data['password']

    # 校验手机号格式
    if not phone.isdigit():
        raise ParamErrorException('手机号格式不正确')

    # 校验验证码
    if not verify_sms_code(phone, 'register', sms_code, mark_used=True):
        raise BusinessException('验证码错误或已过期', code=400002)

    # 检查手机号是否已注册
    if User.objects.filter(phone=phone).exists():
        raise BusinessException('该手机号已注册', code=409001)

    # 创建用户，role 为空字符串（表示未选择身份）
    user = User.objects.create(
        phone=phone,
        hashed_password=_hash_password(password),
        role='',  # 注册成功后 role 为空
        is_active=True,
    )

    tokens = _generate_tokens(user)
    logger.info(f'[Register] user={user.id}, phone={phone}')

    return unified_response(
        data={
            'access_token': tokens['access_token'],
            'refresh_token': tokens['refresh_token'],
            'user': _user_to_dict(user),
        },
        code=ErrorCode.SUCCESS,
    )


@extend_schema(
    request=LoginByPasswordSerializer,
    responses={200: TokenResponseSerializer},
    summary='手机号+密码登录',
    description='手机号+密码登录，返回 token 与用户信息。role 为空时需前端跳转身份选择。',
    tags=['认证'],
)
@api_view(['POST'])
@permission_classes([AllowAny])
def login_by_password(request):
    """
    POST /api/v1/auth/login-by-password
    手机号+密码登录
    """
    serializer = LoginByPasswordSerializer(data=request.data)
    if not serializer.is_valid():
        raise ParamErrorException(serializer.errors)

    phone = serializer.validated_data['phone']
    password = serializer.validated_data['password']

    if not phone.isdigit():
        raise ParamErrorException('手机号格式不正确')

    try:
        user = User.objects.get(phone=phone)
    except User.DoesNotExist:
        raise BusinessException('用户不存在', code=404001)

    if not _check_password(password, user.hashed_password):
        raise BusinessException('密码错误', code=400002)

    if not user.is_active:
        raise BusinessException('账号已被禁用', code=403001)

    tokens = _generate_tokens(user)
    logger.info(f'[LoginByPassword] user={user.id}, phone={phone}')

    return unified_response(
        data={
            'access_token': tokens['access_token'],
            'refresh_token': tokens['refresh_token'],
            'user': _user_to_dict(user),
        },
        code=ErrorCode.SUCCESS,
    )


@extend_schema(
    request=LoginByCodeSerializer,
    responses={200: TokenResponseSerializer},
    summary='手机号+验证码登录',
    description='手机号+验证码登录，无需密码。role 为空时需前端跳转身份选择。',
    tags=['认证'],
)
@api_view(['POST'])
@permission_classes([AllowAny])
def login_by_code(request):
    """
    POST /api/v1/auth/login-by-code
    手机号+验证码登录
    """
    serializer = LoginByCodeSerializer(data=request.data)
    if not serializer.is_valid():
        raise ParamErrorException(serializer.errors)

    phone = serializer.validated_data['phone']
    sms_code = serializer.validated_data['sms_code']

    if not phone.isdigit():
        raise ParamErrorException('手机号格式不正确')

    # 校验验证码
    if not verify_sms_code(phone, 'login', sms_code, mark_used=True):
        raise BusinessException('验证码错误或已过期', code=400002)

    try:
        user = User.objects.get(phone=phone)
    except User.DoesNotExist:
        raise BusinessException('用户不存在', code=404001)

    if not user.is_active:
        raise BusinessException('账号已被禁用', code=403001)

    tokens = _generate_tokens(user)
    logger.info(f'[LoginByCode] user={user.id}, phone={phone}')

    return unified_response(
        data={
            'access_token': tokens['access_token'],
            'refresh_token': tokens['refresh_token'],
            'user': _user_to_dict(user),
        },
        code=ErrorCode.SUCCESS,
    )


@extend_schema(
    request=SelectRoleSerializer,
    responses={200: UserSerializer},
    summary='首次登录选择身份',
    description='首次登录后选择身份（tenant/landlord），仅 role 为空时可调用。',
    tags=['认证'],
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def select_role(request):
    """
    POST /api/v1/auth/select-role
    首次登录选择身份
    """
    serializer = SelectRoleSerializer(data=request.data)
    if not serializer.is_valid():
        raise ParamErrorException(serializer.errors)

    user = request.user
    # 仅 role 为空时可选择
    if user.role:
        raise BusinessException('身份已选择，不可重复操作', code=400002)

    new_role = serializer.validated_data['role']
    user.role = new_role
    user.save(update_fields=['role', 'updated_at'])

    logger.info(f'[SelectRole] user={user.id}, role={new_role}')

    return unified_response(
        data=_user_to_dict(user),
        code=ErrorCode.SUCCESS,
    )


@extend_schema(
    request=ResetPasswordSerializer,
    responses={200: None},
    summary='忘记密码重置',
    description='通过手机号+验证码重置密码。',
    tags=['认证'],
)
@api_view(['POST'])
@permission_classes([AllowAny])
def reset_password(request):
    """
    POST /api/v1/auth/reset-password
    忘记密码重置
    """
    serializer = ResetPasswordSerializer(data=request.data)
    if not serializer.is_valid():
        raise ParamErrorException(serializer.errors)

    phone = serializer.validated_data['phone']
    sms_code = serializer.validated_data['sms_code']
    new_password = serializer.validated_data['new_password']

    if not phone.isdigit():
        raise ParamErrorException('手机号格式不正确')

    # 校验验证码
    if not verify_sms_code(phone, 'reset_password', sms_code, mark_used=True):
        raise BusinessException('验证码错误或已过期', code=400002)

    try:
        user = User.objects.get(phone=phone)
    except User.DoesNotExist:
        raise BusinessException('用户不存在', code=404001)

    user.hashed_password = _hash_password(new_password)
    user.save(update_fields=['hashed_password', 'updated_at'])

    logger.info(f'[ResetPassword] user={user.id}, phone={phone}')

    return unified_response(
        data={'success': True},
        code=ErrorCode.SUCCESS,
    )


@extend_schema(
    request=ChangePasswordSerializer,
    responses={200: None},
    summary='修改密码',
    description='登录用户修改密码，需短信验证码。',
    tags=['认证'],
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password(request):
    """
    POST /api/v1/auth/change-password
    修改密码
    """
    serializer = ChangePasswordSerializer(data=request.data)
    if not serializer.is_valid():
        raise ParamErrorException(serializer.errors)

    user = request.user
    sms_code = serializer.validated_data['sms_code']
    new_password = serializer.validated_data['new_password']

    if not user.phone:
        raise BusinessException('当前用户未绑定手机号', code=400002)

    # 校验验证码
    if not verify_sms_code(user.phone, 'change_password', sms_code, mark_used=True):
        raise BusinessException('验证码错误或已过期', code=400002)

    user.hashed_password = _hash_password(new_password)
    user.save(update_fields=['hashed_password', 'updated_at'])

    logger.info(f'[ChangePassword] user={user.id}')

    return unified_response(
        data={'success': True},
        code=ErrorCode.SUCCESS,
    )


@extend_schema(
    request=AdminLoginSerializer,
    responses={200: TokenResponseSerializer},
    summary='管理员账号登录',
    description='管理员使用 username + password 登录。',
    tags=['认证'],
)
@api_view(['POST'])
@permission_classes([AllowAny])
def admin_login(request):
    """
    POST /api/v1/auth/admin-login
    管理员账号登录
    """
    serializer = AdminLoginSerializer(data=request.data)
    if not serializer.is_valid():
        raise ParamErrorException(serializer.errors)

    username = serializer.validated_data['username']
    password = serializer.validated_data['password']

    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        raise BusinessException('管理员账号不存在', code=404001)

    if not _check_password(password, user.hashed_password):
        raise BusinessException('密码错误', code=400002)

    if not user.is_active:
        raise BusinessException('账号已被禁用', code=403001)

    if user.role != 'admin':
        raise BusinessException('非管理员账号', code=403001)

    tokens = _generate_tokens(user)
    logger.info(f'[AdminLogin] user={user.id}, username={username}')

    return unified_response(
        data={
            'access_token': tokens['access_token'],
            'refresh_token': tokens['refresh_token'],
            'user': _user_to_dict(user),
        },
        code=ErrorCode.SUCCESS,
    )


@extend_schema(
    responses={200: UserSerializer},
    summary='获取当前登录用户',
    description='获取当前登录用户信息。',
    tags=['认证'],
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me(request):
    """
    GET /api/v1/auth/me
    获取当前登录用户
    """
    user = request.user
    return unified_response(
        data=_user_to_dict(user),
        code=ErrorCode.SUCCESS,
    )
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

"""
用户认证相关序列化器
"""
from rest_framework import serializers


class RegisterSerializer(serializers.Serializer):
    """注册请求序列化器"""
    phone = serializers.CharField(max_length=11, min_length=11, help_text='手机号，11位数字')
    sms_code = serializers.CharField(max_length=6, min_length=6, help_text='短信验证码')
    password = serializers.CharField(max_length=128, min_length=6, help_text='密码，至少6位')


class LoginByPasswordSerializer(serializers.Serializer):
    """用户名+密码登录请求序列化器"""
    username = serializers.CharField(max_length=50, help_text='用户名（普通用户为手机号）')
    password = serializers.CharField(max_length=128, help_text='密码')


class LoginByCodeSerializer(serializers.Serializer):
    """手机号+验证码登录请求序列化器"""
    phone = serializers.CharField(max_length=11, min_length=11, help_text='手机号，11位数字')
    sms_code = serializers.CharField(max_length=6, min_length=6, help_text='短信验证码')


class SelectRoleSerializer(serializers.Serializer):
    """首次登录选择身份请求序列化器"""
    role = serializers.ChoiceField(
        choices=['tenant', 'landlord'],
        help_text='身份：tenant(租客) / landlord(商家)',
    )


class ResetPasswordSerializer(serializers.Serializer):
    """忘记密码重置请求序列化器"""
    phone = serializers.CharField(max_length=11, min_length=11, help_text='手机号')
    sms_code = serializers.CharField(max_length=6, min_length=6, help_text='短信验证码')
    new_password = serializers.CharField(max_length=128, min_length=6, help_text='新密码，至少6位')


class ChangePasswordSerializer(serializers.Serializer):
    """修改密码请求序列化器"""
    sms_code = serializers.CharField(max_length=6, min_length=6, help_text='短信验证码')
    new_password = serializers.CharField(max_length=128, min_length=6, help_text='新密码，至少6位')


class TokenResponseSerializer(serializers.Serializer):
    """登录成功响应序列化器"""
    access_token = serializers.CharField(help_text='访问令牌')
    refresh_token = serializers.CharField(help_text='刷新令牌')
    user = serializers.DictField(help_text='用户信息')


class UserSerializer(serializers.Serializer):
    """用户信息序列化器"""
    id = serializers.IntegerField(help_text='用户ID')
    phone = serializers.CharField(help_text='手机号', allow_null=True)
    username = serializers.CharField(help_text='管理员账号', allow_null=True)
    role = serializers.CharField(help_text='角色', allow_null=True)
    is_active = serializers.BooleanField(help_text='是否启用')

"""
用户、验证码与短信日志模型
"""
from django.db import models
from core.models import BaseModel, SoftDeleteManager, AllObjectsManager


class User(BaseModel):
    ROLE_CHOICES = [
        ('tenant', '租客'),
        ('landlord', '商家'),
        ('admin', '管理员'),
    ]

    username = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        unique=True,
        verbose_name='管理员登录账号',
    )
    phone = models.CharField(
        max_length=11,
        null=True,
        blank=True,
        unique=True,
        verbose_name='手机号',
    )
    hashed_password = models.CharField(
        max_length=255,
        verbose_name='加密密码',
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        db_index=True,
        verbose_name='角色',
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='是否启用',
    )

    objects = SoftDeleteManager()
    all_objects = AllObjectsManager()

    class Meta:
        db_table = 'users'
        verbose_name = '用户'
        verbose_name_plural = '用户'
        indexes = [
            models.Index(fields=['role']),
        ]

    def __str__(self):
        return self.username or self.phone or f'User({self.id})'


class VerifyCode(BaseModel):
    PURPOSE_CHOICES = [
        ('register', '注册'),
        ('login', '登录'),
        ('reset_password', '重置密码'),
        ('change_password', '修改密码'),
    ]

    phone = models.CharField(
        max_length=11,
        verbose_name='手机号',
    )
    purpose = models.CharField(
        max_length=20,
        choices=PURPOSE_CHOICES,
        verbose_name='用途',
    )
    code = models.CharField(
        max_length=6,
        verbose_name='验证码',
    )
    used = models.BooleanField(
        default=False,
        verbose_name='是否已使用',
    )
    expired_at = models.DateTimeField(
        verbose_name='过期时间',
    )

    objects = SoftDeleteManager()
    all_objects = AllObjectsManager()

    class Meta:
        db_table = 'verify_codes'
        verbose_name = '短信验证码'
        verbose_name_plural = '短信验证码'
        indexes = [
            models.Index(fields=['phone', 'purpose', 'created_at']),
        ]

    def __str__(self):
        return f'VerifyCode({self.phone} - {self.purpose})'


class SmsLog(models.Model):
    STATUS_CHOICES = [
        ('pending', '待发送'),
        ('success', '成功'),
        ('failed', '失败'),
        ('mock', '模拟'),
    ]

    phone = models.CharField(
        max_length=11,
        verbose_name='接收手机号',
    )
    template_code = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name='短信模板 CODE',
    )
    params = models.JSONField(
        null=True,
        blank=True,
        verbose_name='模板参数',
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        verbose_name='发送状态',
    )
    response = models.TextField(
        null=True,
        blank=True,
        verbose_name='发送结果/错误',
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='创建时间',
    )

    objects = models.Manager()

    class Meta:
        db_table = 'sms_logs'
        verbose_name = '短信发送日志'
        verbose_name_plural = '短信发送日志'
        indexes = [
            models.Index(fields=['phone', 'created_at']),
        ]

    def __str__(self):
        return f'SmsLog({self.phone} - {self.status})'

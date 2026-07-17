"""
验证码服务：生成、频控、校验
"""
import logging
from datetime import timedelta
from django.utils import timezone
from apps.users.models import VerifyCode
from core.sms import generate_sms_code, send_sms
from core.exceptions import TooManyRequestsException, BusinessException

logger = logging.getLogger('apps')

# 频控常量
SMS_COOLDOWN_SECONDS = 60          # 同一手机号同一用途 1 分钟内限发 1 次
SMS_HOURLY_LIMIT = 10              # 同一手机号 1 小时内限发 10 次
SMS_CODE_VALID_MINUTES = 5         # 验证码有效期 5 分钟


def check_sms_rate_limit(phone, purpose):
    """
    检查短信频控
    1. 同一手机号同一用途 1 分钟内只能发 1 次
    2. 同一手机号 1 小时内最多发 10 次（跨用途）
    超频抛出 TooManyRequestsException(429001)
    """
    now = timezone.now()

    # 规则1：1 分钟冷却（同一手机号+用途）
    one_min_ago = now - timedelta(seconds=SMS_COOLDOWN_SECONDS)
    recent_same = VerifyCode.objects.filter(
        phone=phone,
        purpose=purpose,
        created_at__gte=one_min_ago,
    ).exists()
    if recent_same:
        raise TooManyRequestsException('发送过于频繁，请稍后再试')

    # 规则2：1 小时总量限制（同一手机号，跨用途）
    one_hour_ago = now - timedelta(hours=1)
    hourly_count = VerifyCode.objects.filter(
        phone=phone,
        created_at__gte=one_hour_ago,
    ).count()
    if hourly_count >= SMS_HOURLY_LIMIT:
        raise TooManyRequestsException('该手机号今日发送次数已达上限，请稍后再试')


def create_and_send_sms_code(phone, purpose):
    """
    生成验证码、检查频控、发送短信（mock）、保存记录
    返回 dict: {code: str, expires_in: int}
    """
    # 频控检查
    check_sms_rate_limit(phone, purpose)

    # 生成验证码
    code = generate_sms_code()

    # 发送短信（mock）
    template_code = 'SMS_VERIFY_CODE'  # 预留模板 CODE
    success, response = send_sms(phone, template_code=template_code, params={'code': code})
    if not success:
        raise BusinessException('短信发送失败，请稍后重试')

    # 保存验证码记录
    expired_at = timezone.now() + timedelta(minutes=SMS_CODE_VALID_MINUTES)
    VerifyCode.objects.create(
        phone=phone,
        purpose=purpose,
        code=code,
        used=False,
        expired_at=expired_at,
    )

    logger.info(f'[VerifyCode] created: phone={phone}, purpose={purpose}, code={code}, expires_at={expired_at}')

    return {
        'code': code,  # V1.0 mock 模式下返回验证码便于调试；生产环境可移除
        'expires_in': SMS_CODE_VALID_MINUTES * 60,
    }


def verify_sms_code(phone, purpose, code, mark_used=True):
    """
    校验验证码
    - 必须未使用
    - 必须未过期
    - 校验成功后可选标记为已使用
    返回 bool: True=校验通过
    """
    now = timezone.now()
    try:
        record = VerifyCode.objects.filter(
            phone=phone,
            purpose=purpose,
            code=code,
            used=False,
            expired_at__gt=now,
        ).latest('created_at')
    except VerifyCode.DoesNotExist:
        return False

    if mark_used:
        record.used = True
        record.save(update_fields=['used', 'updated_at'])

    return True

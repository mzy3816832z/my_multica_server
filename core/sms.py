"""
短信服务：mock 发送与阿里云短信预留适配
"""
import logging
import random
import string
from django.conf import settings
from apps.users.models import SmsLog

logger = logging.getLogger('apps')


def generate_sms_code(length=6):
    """生成纯数字验证码"""
    return ''.join(random.choices(string.digits, k=length))


def send_sms_mock(phone, template_code=None, params=None):
    """
    Mock 短信发送：仅记录日志，不实际发送
    返回 (success: bool, response: str)
    """
    code = params.get('code') if params else None
    logger.info(f'[SMS MOCK] phone={phone}, template={template_code}, code={code}')
    return True, f'mock_send_ok: code={code}'


def send_sms(phone, template_code=None, params=None):
    """
    统一短信发送入口
    根据 SMS_PROVIDER 配置选择 provider
    返回 (success: bool, response: str)
    """
    provider = getattr(settings, 'SMS_PROVIDER', 'mock')

    if provider == 'mock':
        success, response = send_sms_mock(phone, template_code, params)
    elif provider == 'aliyun':
        # 预留阿里云短信适配，当前降级为 mock
        logger.warning('[SMS] aliyun provider not implemented yet, fallback to mock')
        success, response = send_sms_mock(phone, template_code, params)
    else:
        logger.warning(f'[SMS] unknown provider {provider}, fallback to mock')
        success, response = send_sms_mock(phone, template_code, params)

    # 记录发送日志
    status = 'mock' if provider == 'mock' else ('success' if success else 'failed')
    SmsLog.objects.create(
        phone=phone,
        template_code=template_code,
        params=params,
        status=status,
        response=response,
    )

    return success, response

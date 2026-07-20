"""
管理员审核模块视图
"""
import logging
from django.db import transaction
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema

from core.response import unified_response, ErrorCode
from core.exceptions import BusinessException, NotFoundException
from core.permissions import IsAdmin
from core.pagination import StandardPagination
from core.sms import send_sms
from apps.audits.models import AuditRecord
from apps.audits.serializers import (
    AuditListItemSerializer,
    AuditDetailSerializer,
    AuditApproveSerializer,
    AuditRejectSerializer,
    AuditActionResponseSerializer,
)
from apps.apartments.models import RoomType, RentalPlan
from apps.messages_app.models import Message

logger = logging.getLogger('apps')


# ============================================================
# 管理员审核接口
# ============================================================

@extend_schema(
    request=None,
    responses={200: AuditListItemSerializer(many=True)},
    summary='审核单列表',
    description='管理员查看审核单列表。支持按 type、status 筛选，按提交时间倒序。',
    tags=['管理员审核'],
    parameters=[
        {'name': 'type', 'in': 'query', 'schema': {'type': 'string'}, 'description': '审核类型：first_review / change_review'},
        {'name': 'status', 'in': 'query', 'schema': {'type': 'string'}, 'description': '审核状态：pending / approved / rejected'},
        {'name': 'page', 'in': 'query', 'schema': {'type': 'integer'}, 'description': '页码，默认 1'},
        {'name': 'page_size', 'in': 'query', 'schema': {'type': 'integer'}, 'description': '每页条数，默认 10，最大 100'},
    ],
)
@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdmin])
def audit_list(request):
    """
    GET /api/v1/admin/audits
    审核单列表（管理员）
    """
    queryset = AuditRecord.objects.filter(deleted_at__isnull=True).order_by('-created_at')

    # 按类型筛选
    audit_type = request.query_params.get('type')
    if audit_type:
        queryset = queryset.filter(type=audit_type)

    # 按状态筛选
    audit_status = request.query_params.get('status')
    if audit_status:
        queryset = queryset.filter(status=audit_status)

    paginator = StandardPagination()
    page = paginator.paginate_queryset(queryset, request)
    serializer = AuditListItemSerializer(page, many=True)
    return paginator.get_paginated_response(serializer.data)


@extend_schema(
    request=None,
    responses={200: AuditDetailSerializer},
    summary='审核详情',
    description='管理员查看审核单详情。变更审核返回 original_data、submitted_data、changed_fields。',
    tags=['管理员审核'],
    parameters=[
        {'name': 'id', 'in': 'path', 'schema': {'type': 'integer'}, 'description': '审核单 ID'},
    ],
)
@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdmin])
def audit_detail(request, id):
    """
    GET /api/v1/admin/audits/{id}
    审核详情（管理员）
    """
    try:
        audit = AuditRecord.objects.get(id=id, deleted_at__isnull=True)
    except AuditRecord.DoesNotExist:
        raise NotFoundException('审核单不存在')

    serializer = AuditDetailSerializer(audit)
    return unified_response(data=serializer.data)


@extend_schema(
    request=AuditApproveSerializer,
    responses={200: AuditActionResponseSerializer},
    summary='通过审核',
    description=(
        '管理员通过审核。首次审核通过将公寓置为 published；'
        '变更审核通过后将 submitted_data 快照覆盖原房源（房型全量替换）。'
    ),
    tags=['管理员审核'],
    parameters=[
        {'name': 'id', 'in': 'path', 'schema': {'type': 'integer'}, 'description': '审核单 ID'},
    ],
)
@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdmin])
def audit_approve(request, id):
    """
    POST /api/v1/admin/audits/{id}/approve
    通过审核（管理员）
    """
    try:
        audit = AuditRecord.objects.get(id=id, deleted_at__isnull=True)
    except AuditRecord.DoesNotExist:
        raise NotFoundException('审核单不存在')

    if audit.status != 'pending':
        raise BusinessException('该审核单已处理，无法再次操作', code=ErrorCode.BUSINESS_ERROR)

    apartment = audit.apartment
    reviewer = request.user

    with transaction.atomic():
        if audit.type == 'first_review':
            # 首次审核通过：公寓置为 published
            apartment.status = 'published'
            apartment.save(update_fields=['status'])
        elif audit.type == 'change_review':
            # 变更审核通过：用 submitted_data 覆盖原房源
            _apply_submitted_data(apartment, audit.submitted_data)

        # 更新审核单状态
        audit.status = 'approved'
        audit.reviewer = reviewer
        audit.save(update_fields=['status', 'reviewer'])

    logger.info(f'[AuditApprove] reviewer={reviewer.id}, audit={audit.id}, type={audit.type}')

    return unified_response(
        data={
            'audit_id': audit.id,
            'apartment_id': apartment.id,
            'action': 'approve',
            'status': audit.status,
        },
        code=ErrorCode.SUCCESS,
    )


@extend_schema(
    request=AuditRejectSerializer,
    responses={200: AuditActionResponseSerializer},
    summary='驳回审核',
    description=(
        '管理员驳回审核。首次审核驳回将公寓置为 first_rejected；'
        '变更审核驳回保留原房源 published 状态，审核单作废。'
        '驳回后发送站内信与短信通知商家。'
    ),
    tags=['管理员审核'],
    parameters=[
        {'name': 'id', 'in': 'path', 'schema': {'type': 'integer'}, 'description': '审核单 ID'},
    ],
)
@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdmin])
def audit_reject(request, id):
    """
    POST /api/v1/admin/audits/{id}/reject
    驳回审核（管理员）
    """
    try:
        audit = AuditRecord.objects.get(id=id, deleted_at__isnull=True)
    except AuditRecord.DoesNotExist:
        raise NotFoundException('审核单不存在')

    if audit.status != 'pending':
        raise BusinessException('该审核单已处理，无法再次操作', code=ErrorCode.BUSINESS_ERROR)

    serializer = AuditRejectSerializer(data=request.data)
    if not serializer.is_valid():
        first_msg = _extract_first_error(serializer.errors)
        raise BusinessException(first_msg, code=ErrorCode.BUSINESS_ERROR)

    reject_reason = serializer.validated_data['reject_reason']
    apartment = audit.apartment
    reviewer = request.user
    landlord = apartment.landlord

    with transaction.atomic():
        if audit.type == 'first_review':
            # 首次审核驳回：公寓置为 first_rejected
            apartment.status = 'first_rejected'
            apartment.save(update_fields=['status'])
        # 变更审核驳回：原房源保持 published，无需修改

        # 更新审核单状态
        audit.status = 'rejected'
        audit.reject_reason = reject_reason
        audit.reviewer = reviewer
        audit.save(update_fields=['status', 'reject_reason', 'reviewer'])

        # 发送站内信
        _send_reject_message(audit, reject_reason)

        # 发送短信（mock）
        if landlord and landlord.phone:
            send_sms(
                phone=landlord.phone,
                template_code='REJECT_NOTIFY',
                params={'reason': reject_reason},
            )

    logger.info(f'[AuditReject] reviewer={reviewer.id}, audit={audit.id}, type={audit.type}')

    return unified_response(
        data={
            'audit_id': audit.id,
            'apartment_id': apartment.id,
            'action': 'reject',
            'status': audit.status,
        },
        code=ErrorCode.SUCCESS,
    )


def _apply_submitted_data(apartment, submitted_data):
    """
    将 submitted_data 快照覆盖到原房源（变更审核通过时）
    """
    # 更新公寓基础字段
    apartment.name = submitted_data.get('name', apartment.name)
    apartment.cover_image = submitted_data.get('cover_image', apartment.cover_image)
    apartment.description = submitted_data.get('description', apartment.description)
    apartment.district_id = submitted_data.get('district_id', apartment.district_id)
    apartment.street_id = submitted_data.get('street_id', apartment.street_id)
    apartment.detail_address = submitted_data.get('detail_address', apartment.detail_address)
    apartment.contact_phone = submitted_data.get('contact_phone', apartment.contact_phone)
    apartment.save()

    # 全量替换房型与租金方案
    room_types_data = submitted_data.get('room_types', [])
    if room_types_data:
        # 软删除原有房型（级联软删除租金方案）
        for rt in apartment.room_types.all():
            rt.delete()

        global_min_rent = None
        for rt_data in room_types_data:
            room_type = RoomType.objects.create(
                apartment=apartment,
                name=rt_data['name'],
                images=rt_data.get('images', []),
                facilities=rt_data.get('facilities', []),
                layout_type=rt_data['layout_type'],
                window_type=rt_data['window_type'],
                orientation=rt_data['orientation'],
                floor=rt_data['floor'],
                sort=rt_data.get('sort', 0),
            )
            for rp_data in rt_data.get('rental_plans', []):
                RentalPlan.objects.create(
                    room_type=room_type,
                    lease_term=rp_data['lease_term'],
                    monthly_rent=rp_data['monthly_rent'],
                    payment_method=rp_data['payment_method'],
                )
                if global_min_rent is None or rp_data['monthly_rent'] < global_min_rent:
                    global_min_rent = rp_data['monthly_rent']

        if global_min_rent is not None:
            apartment.min_monthly_rent = global_min_rent
            apartment.save(update_fields=['min_monthly_rent'])


def _send_reject_message(audit, reject_reason):
    """
    发送驳回站内信
    """
    apartment = audit.apartment
    landlord = apartment.landlord if apartment else None
    if not landlord:
        return

    msg_type = 'first_rejected' if audit.type == 'first_review' else 'change_rejected'
    title = '房源审核被驳回' if audit.type == 'first_review' else '房源变更审核被驳回'
    content = f'您的房源「{apartment.name}」审核未通过。驳回原因：{reject_reason}'

    Message.objects.create(
        user=landlord,
        type=msg_type,
        title=title,
        content=content,
        related_apartment=apartment,
        related_audit=audit,
    )


def _extract_first_error(errors):
    """
    从 serializer.errors 中提取第一个错误信息字符串
    """
    if isinstance(errors, dict):
        for key in errors:
            val = errors[key]
            if isinstance(val, list):
                return str(val[0])
            elif isinstance(val, dict):
                return _extract_first_error(val)
            else:
                return str(val)
    elif isinstance(errors, list):
        return str(errors[0])
    return str(errors)

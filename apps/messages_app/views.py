"""
消息模块视图：站内信列表、标记已读、未读数
"""
import logging
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema

from core.response import unified_response
from core.exceptions import NotFoundException
from core.pagination import StandardPagination
from apps.messages_app.models import Message
from apps.messages_app.serializers import (
    MessageListItemSerializer,
    MessageReadSerializer,
    MessageUnreadCountSerializer,
)

logger = logging.getLogger('apps')


@extend_schema(
    request=None,
    responses={200: MessageListItemSerializer(many=True)},
    summary='站内信列表',
    description='返回当前登录用户的站内信列表，按创建时间倒序，支持分页。',
    tags=['消息'],
    parameters=[
        {'name': 'page', 'in': 'query', 'schema': {'type': 'integer'}, 'description': '页码，默认 1'},
        {'name': 'page_size', 'in': 'query', 'schema': {'type': 'integer'}, 'description': '每页条数，默认 10，最大 100'},
    ],
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def message_list(request):
    """
    GET /api/v1/messages
    站内信列表（当前登录用户）
    """
    user = request.user
    queryset = Message.objects.filter(user=user).order_by('-created_at', '-id')

    paginator = StandardPagination()
    page = paginator.paginate_queryset(queryset, request)
    serializer = MessageListItemSerializer(page, many=True)
    return paginator.get_paginated_response(serializer.data)


@extend_schema(
    request=None,
    responses={200: MessageReadSerializer},
    summary='标记站内信已读',
    description='将指定站内信标记为已读。只能标记属于自己的消息。',
    tags=['消息'],
    parameters=[
        {'name': 'id', 'in': 'path', 'schema': {'type': 'integer'}, 'description': '消息 ID'},
    ],
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def message_read(request, id):
    """
    POST /api/v1/messages/{id}/read
    标记站内信已读
    """
    user = request.user
    try:
        msg = Message.objects.get(id=id, user=user)
    except Message.DoesNotExist:
        raise NotFoundException('消息不存在')

    if not msg.is_read:
        msg.is_read = True
        msg.save(update_fields=['is_read', 'updated_at'])
        logger.info(f'[MessageRead] user={user.id}, message={id}')

    return unified_response(data={
        'id': msg.id,
        'is_read': msg.is_read,
    })


@extend_schema(
    request=None,
    responses={200: MessageUnreadCountSerializer},
    summary='未读消息数',
    description='返回当前登录用户的未读站内信数量。',
    tags=['消息'],
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def message_unread_count(request):
    """
    GET /api/v1/messages/unread-count
    未读消息数
    """
    user = request.user
    count = Message.objects.filter(user=user, is_read=False).count()
    return unified_response(data={'unread_count': count})

"""
核心视图：健康检查等
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework import status
from .response import unified_response, ErrorCode


@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """
    健康检查接口
    GET /health
    """
    return unified_response(
        data={
            'status': 'healthy',
            'service': 'apartment-rental-backend',
        },
        code=ErrorCode.SUCCESS,
        status_code=status.HTTP_200_OK,
    )

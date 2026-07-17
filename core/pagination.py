"""
分页配置
"""
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from .response import ErrorCode


class StandardPagination(PageNumberPagination):
    """
    标准分页器
    """
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response({
            'code': ErrorCode.SUCCESS,
            'message': 'success',
            'data': {
                'items': data,
                'total': self.page.paginator.count,
                'page': self.page.number,
                'page_size': self.get_page_size(self.request),
            },
        })

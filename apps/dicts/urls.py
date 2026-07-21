"""
字典路由
"""
from django.urls import path
from apps.dicts.views import dict_list

urlpatterns = [
    path('', dict_list, name='dict-list'),
]

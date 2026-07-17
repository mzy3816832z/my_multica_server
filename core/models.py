"""
通用基础模型与工具
"""
from django.db import models


class BaseModel(models.Model):
    """
    抽象基础模型：包含创建时间、更新时间、逻辑删除时间
    """
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    deleted_at = models.DateTimeField(null=True, blank=True, default=None, verbose_name='逻辑删除时间')

    class Meta:
        abstract = True


class SoftDeleteManager(models.Manager):
    """
    软删除管理器：默认排除已逻辑删除的记录
    """
    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)


class AllObjectsManager(models.Manager):
    """
    全量管理器：包含已逻辑删除的记录
    """
    def get_queryset(self):
        return super().get_queryset()

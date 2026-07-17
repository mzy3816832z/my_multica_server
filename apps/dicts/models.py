"""
系统字典模型
"""
from django.db import models
from core.models import BaseModel, SoftDeleteManager, AllObjectsManager


class SystemDict(BaseModel):
    category = models.CharField(
        max_length=30,
        verbose_name='字典分类',
    )
    code = models.CharField(
        max_length=30,
        verbose_name='字典编码',
    )
    label = models.CharField(
        max_length=50,
        verbose_name='展示文案',
    )
    sort = models.IntegerField(
        default=0,
        verbose_name='排序',
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='是否启用',
    )

    objects = SoftDeleteManager()
    all_objects = AllObjectsManager()

    class Meta:
        db_table = 'system_dicts'
        verbose_name = '系统字典'
        verbose_name_plural = '系统字典'
        indexes = [
            models.Index(fields=['category']),
        ]
        unique_together = [('category', 'code')]

    def __str__(self):
        return f'{self.category}:{self.code}({self.label})'

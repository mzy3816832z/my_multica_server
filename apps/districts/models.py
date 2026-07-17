"""
行政区划模型
"""
from django.db import models
from core.models import BaseModel, SoftDeleteManager, AllObjectsManager


class District(BaseModel):
    LEVEL_CHOICES = [
        (1, '行政区'),
        (2, '街道/镇'),
    ]

    parent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='children',
        verbose_name='父级区划',
    )
    name = models.CharField(
        max_length=50,
        verbose_name='区划名称',
    )
    level = models.SmallIntegerField(
        choices=LEVEL_CHOICES,
        verbose_name='层级',
    )
    code = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name='官方编码',
    )
    sort = models.IntegerField(
        default=0,
        verbose_name='排序',
    )

    objects = SoftDeleteManager()
    all_objects = AllObjectsManager()

    class Meta:
        db_table = 'districts'
        verbose_name = '行政区划'
        verbose_name_plural = '行政区划'
        indexes = [
            models.Index(fields=['parent']),
            models.Index(fields=['level']),
        ]

    def __str__(self):
        return self.name

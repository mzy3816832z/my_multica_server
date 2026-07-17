"""
站内信模型
"""
from django.db import models
from core.models import BaseModel, SoftDeleteManager, AllObjectsManager


class Message(BaseModel):
    TYPE_CHOICES = [
        ('first_rejected', '首次审核驳回'),
        ('change_rejected', '变更审核驳回'),
    ]

    user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name='接收用户',
    )
    type = models.CharField(
        max_length=30,
        choices=TYPE_CHOICES,
        verbose_name='消息类型',
    )
    title = models.CharField(
        max_length=100,
        verbose_name='标题',
    )
    content = models.TextField(
        verbose_name='内容',
    )
    related_apartment = models.ForeignKey(
        'apartments.Apartment',
        on_delete=models.CASCADE,
        related_name='related_messages',
        verbose_name='关联房源',
    )
    related_audit = models.ForeignKey(
        'audits.AuditRecord',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='related_messages',
        verbose_name='关联审核单',
    )
    is_read = models.BooleanField(
        default=False,
        verbose_name='是否已读',
    )

    objects = SoftDeleteManager()
    all_objects = AllObjectsManager()

    class Meta:
        db_table = 'messages'
        verbose_name = '站内信'
        verbose_name_plural = '站内信'
        indexes = [
            models.Index(fields=['user', 'is_read', 'deleted_at']),
            models.Index(fields=['related_apartment']),
        ]

    def __str__(self):
        return self.title

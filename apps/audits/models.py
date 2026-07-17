"""
审核记录模型
"""
from django.db import models
from core.models import BaseModel, SoftDeleteManager, AllObjectsManager


class AuditRecord(BaseModel):
    TYPE_CHOICES = [
        ('first_review', '首次审核'),
        ('change_review', '变更审核'),
    ]
    STATUS_CHOICES = [
        ('pending', '待审核'),
        ('approved', '已通过'),
        ('rejected', '已驳回'),
    ]

    apartment = models.ForeignKey(
        'apartments.Apartment',
        on_delete=models.CASCADE,
        related_name='audit_records',
        verbose_name='关联房源',
    )
    type = models.CharField(
        max_length=30,
        choices=TYPE_CHOICES,
        verbose_name='审核类型',
    )
    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='审核状态',
    )
    submitted_data = models.JSONField(
        verbose_name='提交时完整房源快照',
    )
    original_data = models.JSONField(
        null=True,
        blank=True,
        verbose_name='原房源快照',
    )
    changed_fields = models.JSONField(
        default=list,
        verbose_name='变更字段名列表',
    )
    reject_reason = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        verbose_name='驳回原因',
    )
    reviewer = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_audits',
        verbose_name='审核管理员',
    )

    objects = SoftDeleteManager()
    all_objects = AllObjectsManager()

    class Meta:
        db_table = 'audit_records'
        verbose_name = '审核记录'
        verbose_name_plural = '审核记录'
        indexes = [
            models.Index(fields=['apartment', 'deleted_at']),
            models.Index(fields=['type', 'status', 'deleted_at']),
            models.Index(fields=['reviewer']),
        ]

    def __str__(self):
        return f'Audit({self.apartment.name} - {self.get_type_display()})'

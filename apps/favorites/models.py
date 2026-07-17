"""
收藏模型
"""
from django.db import models
from core.models import BaseModel, SoftDeleteManager, AllObjectsManager


class Favorite(BaseModel):
    user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='favorites',
        verbose_name='用户',
    )
    apartment = models.ForeignKey(
        'apartments.Apartment',
        on_delete=models.CASCADE,
        related_name='favorited_by',
        verbose_name='公寓',
    )

    objects = SoftDeleteManager()
    all_objects = AllObjectsManager()

    class Meta:
        db_table = 'favorites'
        verbose_name = '收藏'
        verbose_name_plural = '收藏'
        indexes = [
            models.Index(fields=['user', 'deleted_at']),
            models.Index(fields=['apartment']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'apartment'],
                condition=models.Q(deleted_at__isnull=True),
                name='unique_user_apartment_favorite',
            ),
        ]

    def __str__(self):
        return f'Favorite({self.user} - {self.apartment})'

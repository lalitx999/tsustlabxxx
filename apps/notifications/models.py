from django.db import models


class StaffNotification(models.Model):
    """Outbox row written inside the business transaction; a Celery task delivers it."""
    CHANNEL_CHOICES = [('line', 'LINE'), ('wechat', 'WeChat')]

    event_key = models.CharField(max_length=160)
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES)
    event_type = models.CharField(max_length=40)
    payload = models.JSONField(default=dict)
    status = models.CharField(max_length=32, default='awaiting_configuration')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'api_staffnotification'
        constraints = [models.UniqueConstraint(fields=['event_key', 'channel'], name='unique_staff_notification_event')]

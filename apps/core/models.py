from django.conf import settings
from django.db import models


class GeneratedFile(models.Model):
    """A file built by a Celery task (certificate PDF, report PDF, label, photo ZIP).

    The request only creates this row and queues the task; the browser polls the
    status endpoint and downloads when ready. Same `cache_key` reuses the file.
    """
    KIND_CHOICES = [
        ('certificate_pdf', 'Certificate PDF'),
        ('daily_report_pdf', 'Daily report PDF'),
        ('return_label_pdf', 'Return label PDF'),
        ('photo_zip', 'Job photos ZIP'),
    ]
    STATUS_CHOICES = [('pending', 'Pending'), ('ready', 'Ready'), ('failed', 'Failed')]

    kind = models.CharField(max_length=30, choices=KIND_CHOICES)
    cache_key = models.CharField(max_length=200, unique=True)
    params = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    file = models.FileField(upload_to='generated/%Y/%m/', blank=True)
    filename = models.CharField(max_length=150)
    content_type = models.CharField(max_length=80, default='application/pdf')
    is_public = models.BooleanField(default=False)
    error = models.TextField(blank=True, default='')
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=['kind', 'status'])]

    def __str__(self):
        return f'{self.kind}:{self.cache_key} ({self.status})'

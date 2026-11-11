from django.conf import settings
from django.db import models


class WorkflowEvent(models.Model):
    """Audit trail of staff actions (payments, check-in, inspection, refunds...)."""
    booking = models.ForeignKey('bookings.Booking', on_delete=models.CASCADE, null=True, blank=True)
    job = models.ForeignKey('inspections.Job', on_delete=models.CASCADE, null=True, blank=True)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    action = models.CharField(max_length=50)
    detail = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'api_workflowevent'
        indexes = [models.Index(fields=['action', 'created_at'], name='workflow_action_created_idx')]

"""Staff notification outbox.

Rows are written inside the business transaction (rolled-back work never
notifies anyone). Delivery happens in Celery after commit.
"""
from django.db import transaction

from apps.notifications.models import StaffNotification


def queue_staff_notification(event_key, event_type, payload, channels=('line', 'wechat')):
    from apps.notifications.tasks import deliver_staff_notification

    for channel in channels:
        item, created = StaffNotification.objects.get_or_create(
            event_key=event_key, channel=channel,
            defaults={'event_type': event_type, 'payload': payload},
        )
        if created:
            transaction.on_commit(lambda pk=item.pk: deliver_staff_notification.delay(pk))

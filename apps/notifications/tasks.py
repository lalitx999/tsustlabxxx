"""Background delivery: e-mail, LINE, WeChat. Network calls never run in a web request."""
import logging

import requests
from celery import shared_task
from django.conf import settings

from apps.notifications.models import StaffNotification
from apps.notifications.services import email_service, line_service

logger = logging.getLogger(__name__)
RETRY = dict(autoretry_for=(requests.RequestException, OSError), retry_backoff=30, max_retries=5)


@shared_task(**RETRY)
def send_payment_confirmation_email(booking_id: int) -> None:
    from apps.bookings.models import Booking
    booking = Booking.objects.select_related('customer').filter(pk=booking_id).first()
    if booking:
        email_service.send_payment_confirmation(booking)


@shared_task(**RETRY)
def send_inspection_result_email(job_id: int) -> None:
    from apps.inspections.models import Job
    job = Job.objects.select_related('customer', 'certificate').filter(pk=job_id).first()
    if job:
        email_service.send_inspection_result(job)


@shared_task(**RETRY)
def send_certificate_email(certificate_id: int, recipient: str = '') -> None:
    from apps.inspections.models import Certificate
    cert = Certificate.objects.select_related('job__customer').filter(pk=certificate_id).first()
    if cert:
        email_service.send_certificate(cert, recipient or None)


@shared_task(**RETRY)
def send_certificate_line(certificate_id: int, line_user_id: str) -> None:
    from apps.inspections.models import Certificate
    cert = Certificate.objects.select_related('job').filter(pk=certificate_id).first()
    if cert:
        verify_url = f'{settings.SITE_URL}/verify/?id={cert.cert_code}'
        line_service.push_message(line_user_id, [line_service.certificate_message(cert, verify_url)])


@shared_task(**RETRY)
def notify_line_new_booking(booking_id: int) -> None:
    from apps.bookings.models import Booking
    booking = Booking.objects.select_related('customer').filter(pk=booking_id).first()
    if booking and settings.LINE_GROUP_ID:
        line_service.push_message(settings.LINE_GROUP_ID, [line_service.booking_flex_message(booking)])


@shared_task(**RETRY)
def deliver_staff_notification(notification_id: int) -> None:
    """Deliver one outbox row. Channels without configuration stay 'awaiting_configuration'."""
    item = StaffNotification.objects.filter(pk=notification_id).first()
    if not item or item.status == 'sent':
        return
    text = f'[TRUST LAB] {item.event_type}: ' + ', '.join(f'{k}={v}' for k, v in item.payload.items())
    if item.channel == 'wechat' and settings.WECHAT_WORK_WEBHOOK_URL:
        requests.post(settings.WECHAT_WORK_WEBHOOK_URL, json={'msgtype': 'text', 'text': {'content': text}},
                      timeout=settings.EXTERNAL_HTTP_TIMEOUT).raise_for_status()
    elif item.channel == 'line' and settings.LINE_GROUP_ID and settings.LINE_CHANNEL_ACCESS_TOKEN:
        line_service.push_message(settings.LINE_GROUP_ID, [{'type': 'text', 'text': text}])
    else:
        return
    StaffNotification.objects.filter(pk=item.pk).update(status='sent')

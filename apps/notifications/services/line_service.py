"""LINE Messaging API calls. Only ever called from Celery tasks (network I/O)."""
import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)
PUSH_URL = 'https://api.line.me/v2/bot/message/push'


def push_message(target_id: str, messages: list) -> dict:
    token = settings.LINE_CHANNEL_ACCESS_TOKEN
    if not token or not target_id:
        logger.info('LINE push skipped: token or target not configured')
        return {'status': 'skipped'}
    response = requests.post(
        PUSH_URL,
        json={'to': target_id, 'messages': messages},
        headers={'Authorization': f'Bearer {token}'},
        timeout=settings.EXTERNAL_HTTP_TIMEOUT,
    )
    if response.status_code != 200:
        logger.error('LINE push failed (%s): %s', response.status_code, response.text[:300])
        response.raise_for_status()
    return {'status': 'sent'}


def booking_flex_message(booking) -> dict:
    """Compact Flex bubble announcing a new booking to the staff group."""
    snapshot = booking.price_snapshot or {}
    rows = [
        ('ลูกค้า', booking.customer.full_name),
        ('สินค้า', f'{booking.brand_name} {booking.model}'.strip() or '-'),
        ('นัดหมาย', f'{booking.booking_date:%d/%m/%Y} {booking.booking_time:%H:%M}'),
        ('แพ็กเกจ', booking.service_package or '-'),
        ('ยอดรวม', f"{snapshot.get('total', '0.00')} บาท"),
        ('ชำระเงิน', booking.payment_status_label),
    ]
    contents = [{'type': 'text', 'text': f'จองใหม่ {booking.display_id}', 'weight': 'bold', 'size': 'lg'}]
    for label, value in rows:
        contents.append({
            'type': 'box', 'layout': 'baseline', 'spacing': 'sm', 'contents': [
                {'type': 'text', 'text': label, 'color': '#888888', 'size': 'sm', 'flex': 2},
                {'type': 'text', 'text': str(value), 'size': 'sm', 'flex': 5, 'wrap': True},
            ],
        })
    return {
        'type': 'flex',
        'altText': f'TRUST LAB: จองใหม่ {booking.display_id}',
        'contents': {'type': 'bubble', 'body': {'type': 'box', 'layout': 'vertical', 'spacing': 'md', 'contents': contents}},
    }


def certificate_message(cert, verify_url: str) -> dict:
    return {'type': 'text', 'text': (
        'TRUST LAB THAILAND\n'
        f'ใบรับรองเลขที่ {cert.cert_code}\n'
        f'สินค้า: {cert.job.brand} {cert.job.model}\n'
        f'ตรวจสอบออนไลน์: {verify_url}'
    )}

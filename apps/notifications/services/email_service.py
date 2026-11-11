"""Customer e-mails. Rendered with Django templates (auto-escaped) and sent from Celery."""
from decimal import Decimal

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

PAYMENT_METHOD_LABELS = {
    'cash': 'เงินสด', 'transfer': 'โอนเงิน', 'credit_card': 'บัตรเครดิต',
    'promptpay': 'PromptPay QR', 'wallet': 'เครดิตสะสม (Wallet)',
}
RESULT_LABELS = {
    'authentic': ('AUTHENTIC – ผ่านเกณฑ์', 'authentic'),
    'fake': ('NOT AUTHENTICATED – ไม่ผ่านเกณฑ์การรับรองความแท้', 'fake'),
}
INCONCLUSIVE = ('UNABLE TO AUTHENTICATE – ข้อมูลหรือผลตรวจไม่เพียงพอที่จะสรุป', 'inconclusive')


def _send(subject, recipient, template, context):
    if not recipient or '@' not in recipient:
        return False
    context = {**context, 'site_url': settings.SITE_URL}
    html = render_to_string(template, context)
    message = EmailMultiAlternatives(subject, strip_tags(html), settings.DEFAULT_FROM_EMAIL, [recipient.strip()])
    message.attach_alternative(html, 'text/html')
    return message.send(fail_silently=False) > 0


def send_payment_confirmation(booking) -> bool:
    total = Decimal(str((booking.price_snapshot or {}).get('total', 0)))
    return _send(
        f'[TRUST LAB] ยืนยันการชำระเงินเรียบร้อยแล้ว - รหัส {booking.display_id}',
        booking.customer.email,
        'emails/payment_confirmation.html',
        {'booking': booking, 'total': total,
         'pay_method': PAYMENT_METHOD_LABELS.get(booking.payment_method, booking.payment_method)},
    )


def send_inspection_result(job) -> bool:
    label, badge = RESULT_LABELS.get(job.result, INCONCLUSIVE)
    cert = getattr(job, 'certificate', None)
    cert_code = job.tag_code or (cert.cert_code if cert else '')
    return _send(
        f'[TRUST LAB] แจ้งผลการตรวจสอบสินค้า {job.display_id} ({job.brand} {job.model})',
        job.customer.email,
        'emails/inspection_result.html',
        {'job': job, 'result_label': label, 'badge': badge, 'cert_code': cert_code},
    )


def send_certificate(cert, recipient=None) -> bool:
    status_label = {'authentic': 'AUTHENTIC – ผ่านเกณฑ์', 'unauthentic': 'NOT AUTHENTICATED'}.get(
        cert.cert_status, cert.cert_status.upper())
    return _send(
        f'[TRUST LAB] ใบรับรองสินค้าและผลการตรวจ {cert.cert_code} ({cert.job.brand} {cert.job.model})',
        recipient or cert.job.customer.email,
        'emails/certificate.html',
        {'cert': cert, 'status_label': status_label},
    )

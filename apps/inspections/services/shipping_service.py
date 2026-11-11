"""Return shipping status and the printable return label (built in Celery)."""
import io
import os
from xml.sax.saxutils import escape

from django.conf import settings
from django.db import transaction

from apps.audit.services.audit_service import record_event
from apps.core.exceptions import ServiceError
from apps.core.services.file_service import request_file
from apps.core.utils import clean_text, parse_pk
from apps.inspections.models import Job

TRANSITIONS = {
    'not_applicable': ['delivered'],
    'pending_return': ['ready_to_ship'],
    'ready_to_ship': ['shipped'],
    'shipped': ['delivered'],
    'delivered': [],
}


@transaction.atomic
def update_shipping(job_id, *, new_status, tracking_number, actor) -> str:
    job = Job.objects.select_for_update().filter(pk=parse_pk(job_id)).first()
    if not job:
        raise ServiceError('ไม่พบงาน', status=404)
    if job.status not in ('completed', 'cancelled'):
        raise ServiceError('งานยังไม่พร้อมคืนสินค้า')
    if job.service_package == 'photo_review':
        raise ServiceError('Photo Review ไม่มีการส่งคืนสินค้า')
    if new_status == job.shipping_status:
        return new_status
    if new_status not in TRANSITIONS.get(job.shipping_status, []):
        raise ServiceError('ลำดับสถานะส่งคืนไม่ถูกต้อง')
    tracking = clean_text(tracking_number or job.tracking_number or '', 100)
    if new_status == 'shipped' and not tracking:
        raise ServiceError('กรุณาระบุเลขพัสดุหรืออ้างอิงการจัดส่ง')
    job.shipping_status, job.tracking_number = new_status, tracking
    job.save(update_fields=['shipping_status', 'tracking_number', 'updated_at'])
    record_event(actor, 'shipping', job=job, status=new_status, tracking_number=tracking)
    return new_status


def request_return_label(job_id, user):
    job = Job.objects.select_related('booking').filter(pk=parse_pk(job_id)).first()
    if not job or not job.booking_id or job.booking.delivery_method != 'shipping':
        raise ServiceError('รายการนี้ไม่มีที่อยู่จัดส่งคืน')
    if job.status not in ('completed', 'cancelled') or job.service_package == 'photo_review':
        raise ServiceError('รายการยังไม่พร้อมจัดส่ง')
    if not settings.THAI_FONT_PATH:
        raise ServiceError('กรุณาตั้ง THAI_FONT_PATH ก่อนพิมพ์ใบปะหน้าภาษาไทย')
    return request_file(kind='return_label_pdf', cache_key=f'label:{job.pk}:{job.updated_at.timestamp():.0f}',
                        filename=f'job-{job.pk}-label.pdf', params={'job_id': job.pk}, user=user)


def build_return_label(params: dict) -> bytes:
    """GeneratedFile builder (runs in Celery)."""
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer

    job = Job.objects.select_related('booking').get(pk=params['job_id'])
    booking = job.booking
    if 'TrustLabThai' not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont('TrustLabThai', settings.THAI_FONT_PATH))
    output = io.BytesIO()
    doc = SimpleDocTemplate(output, pagesize=(100 * mm, 150 * mm), leftMargin=8 * mm, rightMargin=8 * mm,
                            topMargin=8 * mm, bottomMargin=8 * mm)
    style = ParagraphStyle('Thai', fontName='TrustLabThai', fontSize=12, leading=19, wordWrap='CJK')
    logo = os.path.join(settings.BASE_DIR, 'static', 'img', 'logo-print.png')
    story = [Image(logo, width=45 * mm, height=15 * mm, kind='proportional'), Spacer(1, 6 * mm)]
    for line in (f'ส่งคืน / RETURN — JOB {job.pk}', booking.return_address_name, booking.return_phone,
                 booking.return_address_detail, f'{booking.return_subdistrict} {booking.return_district}',
                 f'{booking.return_province} {booking.return_postal_code}', f'Tracking: {job.tracking_number or "-"}'):
        story += [Paragraph(escape(line), style), Spacer(1, 2 * mm)]
    doc.build(story)
    return output.getvalue()

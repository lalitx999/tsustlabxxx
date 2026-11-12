import datetime
import uuid

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.audit.services.audit_service import record_event
from apps.core.exceptions import ServiceError
from apps.core.services.file_service import request_file
from apps.core.utils import clean_text
from apps.inspections.models import Certificate, CertificateSendLog, Job

CERT_PACKAGES = ('cert_15d', 'cert_90d')


def _check_code(code: str, exclude_job=None) -> str:
    code = clean_text(code)
    if len(code) > 50 or any(c in code for c in '/?#'):
        raise ServiceError('เลขใบเซอร์ต้องไม่เกิน 50 ตัวอักษร และไม่มี / ? #')
    if code and Certificate.objects.filter(cert_code=code).exclude(job=exclude_job).exists():
        raise ServiceError('เลขใบเซอร์นี้ถูกใช้แล้ว กรุณาใช้เลขอื่น')
    return code


def validity_days_for(job: Job) -> int:
    days = 15 if job.service_package == 'cert_15d' else 90
    try:
        return int((job.price_snapshot or {}).get('validity_days') or days)
    except (TypeError, ValueError):
        return days


def issue_certificate(job: Job, custom_code=None) -> Certificate:
    if job.service_package not in CERT_PACKAGES or job.status != 'completed' or not job.result:
        raise ServiceError('ออกใบรับรองได้เฉพาะงานตรวจสินค้าจริงที่ตรวจเสร็จแล้ว')
    code = _check_code(custom_code or '', exclude_job=job)
    status = 'authentic' if job.result == 'authentic' else 'unauthentic'
    days = validity_days_for(job)
    try:
        with transaction.atomic():
            cert, created = Certificate.objects.get_or_create(job=job, defaults={
                'cert_code': code or f'TL-{uuid.uuid4().hex[:12].upper()}', 'cert_status': status,
                'validity_days': days, 'expires_at': timezone.now() + datetime.timedelta(days=days)})
    except IntegrityError:
        raise ServiceError('เลขใบเซอร์ซ้ำ กรุณาใช้เลขอื่น')
    changed = []
    if not created and cert.cert_status not in ('revoked', 'expired') and cert.cert_status != status:
        cert.cert_status = status
        changed.append('cert_status')
    if not created and code and cert.cert_code != code:
        cert.cert_code = code
        changed.append('cert_code')
    if changed:
        cert.save(update_fields=changed)
    return cert


@transaction.atomic
def issue_for_job(job_id, custom_code, actor) -> Certificate:
    job = Job.objects.select_for_update().filter(pk=job_id).first()
    if not job:
        raise ServiceError('ไม่พบงาน', status=404)
    cert = issue_certificate(job, custom_code)
    record_event(actor, 'issue_certificate', job=job, cert_code=cert.cert_code)
    return cert


@transaction.atomic
def change_code(cert: Certificate, new_code: str) -> Certificate:
    new_code = _check_code(new_code, exclude_job=cert.job)
    if not new_code:
        raise ServiceError('กรุณาระบุเลขใบเซอร์')
    old_code = cert.cert_code
    cert.cert_code = new_code
    cert.save(update_fields=['cert_code', 'updated_at'])
    Job.objects.filter(pk=cert.job_id, tag_code=old_code).update(tag_code=new_code)
    return cert


def revoke(cert: Certificate, reason: str, actor) -> Certificate:
    cert.cert_status, cert.revoke_reason = 'revoked', clean_text(reason, 2000)
    cert.save(update_fields=['cert_status', 'revoke_reason', 'updated_at'])
    record_event(actor, 'certificate_revoked', job=cert.job, cert_code=cert.cert_code)
    return cert


def expire(cert: Certificate, actor) -> Certificate:
    cert.cert_status, cert.expired_at = 'expired', timezone.now()
    cert.save(update_fields=['cert_status', 'expired_at', 'updated_at'])
    record_event(actor, 'certificate_expired', job=cert.job, cert_code=cert.cert_code)
    return cert


MAX_CERT_PHOTOS = 3  # the PDF has one main photo and two small ones


def select_photos(cert: Certificate, photo_ids, actor=None) -> Certificate:
    """Choose (in order) which booking photos appear on the certificate."""
    try:
        ids = list(dict.fromkeys(int(pid) for pid in photo_ids))
    except (TypeError, ValueError):
        raise ServiceError('รหัสรูปภาพไม่ถูกต้อง')
    allowed = set(cert.job.booking.photos.values_list('pk', flat=True)) if cert.job.booking_id else set()
    chosen = [pid for pid in ids if pid in allowed]
    if not chosen:
        raise ServiceError('กรุณาเลือกรูปภาพอย่างน้อย 1 ภาพ')
    if len(chosen) > MAX_CERT_PHOTOS:
        raise ServiceError(f'เลือกรูปภาพได้สูงสุด {MAX_CERT_PHOTOS} ภาพเท่านั้น')
    cert.selected_photos = chosen
    cert.save(update_fields=['selected_photos', 'updated_at'])
    record_event(actor, 'certificate_photos_selected', job=cert.job, photo_ids=chosen)
    return cert


def send(cert: Certificate, method: str, recipient: str) -> CertificateSendLog:
    """Queue delivery (Celery) and log it."""
    from apps.notifications.tasks import send_certificate_email, send_certificate_line

    method = (method or 'email').lower()
    recipient = clean_text(recipient, 255)
    if method not in ('email', 'line'):
        raise ServiceError('ช่องทางส่งไม่ถูกต้อง')
    if method == 'line' and not recipient:
        raise ServiceError('กรุณาระบุ LINE User ID')
    if method == 'email' and not (recipient or cert.job.customer.email):
        raise ServiceError('ลูกค้าไม่มีอีเมล กรุณาระบุอีเมลผู้รับ')
    log = CertificateSendLog.objects.create(certificate=cert, method=method,
                                            recipient=recipient or cert.job.customer.email)
    if method == 'email':
        transaction.on_commit(lambda: send_certificate_email.delay(cert.pk, recipient))
    else:
        transaction.on_commit(lambda: send_certificate_line.delay(cert.pk, recipient))
    return log


def request_pdf(cert: Certificate, user=None):
    """PDF is built in Celery; the cache key changes whenever the certificate changes."""
    if cert.job.service_package == 'photo_review':
        raise ServiceError('Photo Review ไม่มีใบรับรอง', status=404)
    return request_file(
        kind='certificate_pdf',
        cache_key=f'cert:{cert.pk}:{cert.updated_at.timestamp():.0f}:{cert.cert_status}',
        filename=f'certificate_{cert.cert_code or cert.pk}.pdf',
        params={'certificate_id': cert.pk}, user=user, is_public=True)

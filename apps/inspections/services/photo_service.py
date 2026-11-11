"""Staff photos from the camera app, deletion, and ZIP export (built in Celery)."""
import io
import zipfile

from django.db import transaction

from apps.audit.services.audit_service import record_event
from apps.bookings.models import Booking, BookingPhoto
from apps.core.exceptions import ServiceError
from apps.core.services.file_service import request_file
from apps.core.utils import decode_image, parse_pk
from apps.inspections.models import Certificate, Job
from apps.notifications.services.outbox_service import queue_staff_notification

MAX_STAFF_PHOTOS = 30


@transaction.atomic
def add_staff_photos(booking_id, photos, actor) -> list:
    booking = Booking.objects.select_for_update().filter(pk=parse_pk(booking_id)).first()
    if not booking:
        raise ServiceError('ไม่พบรายการ', status=404)
    if not isinstance(photos, list) or not photos:
        raise ServiceError('กรุณาเลือกรูปภาพ')
    existing = booking.photos.filter(photo_type='staff').count()
    if existing + len(photos) > MAX_STAFF_PHOTOS:
        raise ServiceError('แนบภาพเจ้าหน้าที่ได้สูงสุด 30 ภาพต่อรายการ')
    files = [decode_image(p) for p in photos]
    created = []
    for content in files:  # each file must be written to storage individually
        row = BookingPhoto(booking=booking, photo_type='staff')
        row.photo.save(content.name, content, save=False)
        created.append(row)
    BookingPhoto.objects.bulk_create(created)
    ids = [row.pk for row in created]
    job_id = Job.objects.filter(booking=booking).values_list('pk', flat=True).first()
    queue_staff_notification(f'photos:{booking.pk}:{ids[0]}:{ids[-1]}', 'staff_photos_added',
                             {'booking_id': booking.pk, 'job_id': job_id, 'count': len(ids)}, channels=('wechat',))
    record_event(actor, 'photos_added', booking=booking, count=len(ids))
    return [{'id': row.pk, 'url': row.photo.url} for row in created]


@transaction.atomic
def delete_photo(booking_id, photo_id, actor) -> None:
    photo = BookingPhoto.objects.select_related('booking').filter(pk=photo_id, booking_id=parse_pk(booking_id)).first()
    if not photo:
        raise ServiceError('ไม่พบรูปภาพ', status=404)
    cert = Certificate.objects.select_for_update().filter(job__booking_id=photo.booking_id).first()
    if cert and photo.pk in (cert.selected_photos or []):
        cert.selected_photos = [pid for pid in cert.selected_photos if pid != photo.pk]
        cert.save(update_fields=['selected_photos', 'updated_at'])
    photo.photo.delete(save=False)
    photo.delete()
    record_event(actor, 'photo_deleted', booking=photo.booking, photo_id=photo_id)


def request_photo_zip(job_id, user):
    job = Job.objects.filter(pk=parse_pk(job_id)).only('pk', 'booking_id', 'updated_at').first()
    if not job or not job.booking_id:
        raise ServiceError('ไม่พบภาพของงานนี้')
    count = BookingPhoto.objects.filter(booking_id=job.booking_id).count()
    return request_file(kind='photo_zip', cache_key=f'photos:{job.pk}:{count}:{job.updated_at.timestamp():.0f}',
                        filename=f'job-{job.pk}-photos.zip', params={'job_id': job.pk}, user=user,
                        content_type='application/zip')


def build_photo_zip(params: dict) -> bytes:
    job = Job.objects.select_related('booking').get(pk=params['job_id'])
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('job.txt', f'Job {job.pk}\n{job.brand} {job.model}\nSerial: {job.serial_number or "-"}\n')
        for photo in job.booking.photos.all().only('pk', 'photo', 'photo_type'):
            ext = photo.photo.name.rsplit('.', 1)[-1]
            with photo.photo.open('rb') as source:
                archive.writestr(f'{photo.photo_type}-{photo.pk}.{ext}', source.read())
    return buffer.getvalue()

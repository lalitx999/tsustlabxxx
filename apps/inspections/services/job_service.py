"""Receive items (check-in) and record inspection results."""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import Branch
from apps.audit.services.audit_service import record_event
from apps.bookings.models import Booking
from apps.core.exceptions import ServiceError
from apps.core.money import money, vat_included
from apps.core.utils import clean_text, parse_pk
from apps.inspections.models import Job
from apps.notifications.services.outbox_service import queue_staff_notification

ITEM_FIELDS = ('serial_number', 'color', 'material', 'accessories', 'notes', 'expert_instruction', 'tag_code')
RESULTS = ('authentic', 'fake', 'inconclusive')


def set_job_price(job: Job, total) -> None:
    """Keep job price, VAT and both price snapshots in sync (was Job.save in the legacy code)."""
    total = money(total)
    vat = vat_included(total)
    values = {'total': f'{total:.2f}', 'service_amount': f'{total:.2f}',
              'subtotal': f'{total - vat:.2f}', 'vat_amount': f'{vat:.2f}'}
    job.price, job.vat_amount = total, vat
    job.price_snapshot = {**(job.price_snapshot or {}), **values}
    if job.booking_id:
        booking_snapshot = {**(job.booking.price_snapshot or {}), **values}
        Booking.objects.filter(pk=job.booking_id).update(price_snapshot=booking_snapshot)
        job.booking.price_snapshot = booking_snapshot


def _next_queue_no(branch_id) -> str:
    """Daily running number. The branch row lock serialises concurrent check-ins."""
    Branch.objects.select_for_update().get(pk=branch_id)
    count = Job.objects.filter(created_at__date=timezone.localdate()).count()
    return f'{branch_id}-{count + 1:03}'


def apply_item_details(job: Job, data: dict) -> None:
    for field in ITEM_FIELDS:
        if field in data:
            setattr(job, field, clean_text(data[field], Job._meta.get_field(field).max_length))
    if data.get('brand') or data.get('brand_name'):
        job.brand = clean_text(data.get('brand') or data.get('brand_name'), 100)
    for field in ('model', 'category', 'sub_category'):
        if data.get(field):
            setattr(job, field, clean_text(data[field], 100))


@transaction.atomic
def check_in(booking_id, data: dict, actor) -> Job:
    """Create the Job for a booking (or update item details if it already exists)."""
    booking = Booking.objects.select_for_update(of=('self',)).select_related('customer').filter(pk=parse_pk(booking_id)).first()
    if not booking:
        raise ServiceError('ไม่พบรายการจอง', status=404)
    if booking.status == 'cancelled':
        raise ServiceError('รายการถูกยกเลิกแล้ว')
    existing = Job.objects.select_for_update().filter(booking=booking).first()
    if existing:
        apply_item_details(existing, data)
        existing.save()
        return existing
    if not booking.price_snapshot or not booking.service_package:
        raise ServiceError('รายการเดิมต้องตรวจทานแพ็กเกจและราคาใหม่ก่อนรับงาน')
    snapshot = booking.price_snapshot
    job = Job(
        booking=booking, customer=booking.customer, category=booking.category,
        brand=booking.brand_name, model=booking.model, color='', notes=booking.note,
        queue_no=_next_queue_no(booking.branch_id), service_package=booking.service_package,
        price_snapshot=snapshot, price=money(snapshot.get('total', 0)),
        vat_amount=money(snapshot.get('vat_amount', 0)),
        payment_method=booking.payment_method, payment_status=booking.payment_status,
        shipping_status='pending_return' if booking.delivery_method == 'shipping' else 'not_applicable')
    apply_item_details(job, data)
    job.save()
    record_event(actor, 'check_in', booking=booking, job=job)
    queue_staff_notification(f'job:{job.pk}:created', 'job_created', {'job_id': job.pk, 'booking_id': booking.pk})
    return job


@transaction.atomic
def record_result(job_id, data: dict, actor) -> Job:
    """Expert sets status/result. Completing a real inspection issues the certificate."""
    from apps.inspections.services.certificate_service import issue_certificate

    job = (Job.objects.select_for_update(of=('self',)).select_related('booking', 'customer')
           .filter(pk=parse_pk(job_id)).first())
    if not job:
        raise ServiceError('ไม่พบรายการสั่งงานนี้', status=404)
    if job.status == 'cancelled':
        raise ServiceError('งานถูกยกเลิกแล้ว')
    previous = (job.status, job.result, job.expert_source)
    result = data.get('result', job.result) or None
    if result == 'pending':
        result = None
    state = data.get('status', job.status)
    if state not in ('pending', 'in_progress', 'completed') or result not in (None, *RESULTS):
        raise ServiceError('สถานะหรือผลตรวจไม่ถูกต้อง; กรณีตรวจไม่ได้ให้ขอยกเลิก')
    if state == 'completed' and result not in RESULTS:
        raise ServiceError('กรุณาระบุผลตรวจ')
    if hasattr(job, 'certificate') and (result != job.result or state != job.status):
        raise ServiceError('งานมีใบรับรองแล้ว กรุณาเพิกถอนและตรวจทานก่อนเปลี่ยนผล')

    if 'expert_instruction' in data:
        job.expert_instruction = clean_text(data['expert_instruction'], 2000)
    if 'tag_code' in data:
        job.tag_code = clean_text(data['tag_code'], 100)
    job.status, job.result = state, result
    expert_id = data.get('expert_id')
    if expert_id:
        expert = get_user_model().objects.filter(pk=parse_pk(expert_id)).only('full_name', 'username').first()
        if expert:
            job.result_recorded_by, job.expert_source = expert, expert.display_name
    elif data.get('expert_source'):
        job.expert_source = clean_text(data['expert_source'], 255)
    elif not job.result_recorded_by_id:
        job.result_recorded_by = actor
    job.save()

    if state == 'completed':
        if result in ('authentic', 'fake') and job.service_package != 'photo_review':
            issue_certificate(job, custom_code=data.get('cert_code'))
        if job.booking_id:
            Booking.objects.filter(pk=job.booking_id).update(status='completed')
        from apps.notifications.tasks import send_inspection_result_email
        transaction.on_commit(lambda: send_inspection_result_email.delay(job.pk))
    record_event(actor, 'inspection', job=job, result=result, status=state, expert_source=job.expert_source)
    if previous != (job.status, job.result, job.expert_source):
        queue_staff_notification(f'job:{job.pk}:updated:{job.updated_at.isoformat()}', 'job_updated',
                                 {'job_id': job.pk, 'status': job.status, 'result': job.result})
    return job


def override_price(job: Job, total: Decimal, reason: str, actor) -> None:
    if job.payment_status == 'paid':
        raise ServiceError('รายการชำระแล้ว ไม่สามารถแก้ราคาได้')
    if not clean_text(reason):
        raise ServiceError('กรุณาระบุเหตุผลการแก้ราคา')
    set_job_price(job, total)
    job.save(update_fields=['price', 'vat_amount', 'price_snapshot'])
    record_event(actor, 'price_override', job=job, total=total, reason=reason)

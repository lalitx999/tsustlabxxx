"""Cancellation and refunds (same rules as the legacy workflows)."""
from django.db import transaction
from django.utils import timezone

from apps.audit.services.audit_service import record_event
from apps.bookings.models import Booking, CancellationRequest
from apps.core.exceptions import ServiceError
from apps.core.money import money
from apps.core.permissions import is_manager
from apps.core.utils import clean_text
from apps.inspections.models import Certificate, Job


def _cancel_everything(booking: Booking, reason: str, actor, approver=None):
    now = timezone.now()
    booking.status, booking.cancel_reason = 'cancelled', reason
    booking.cancelled_by = actor if actor and actor.is_authenticated else None
    booking.cancelled_at = now
    booking.save(update_fields=['status', 'cancel_reason', 'cancelled_by', 'cancelled_at'])
    job_fields = {'status': 'cancelled', 'cancel_reason': reason, 'cancelled_by': booking.cancelled_by,
                  'cancelled_at': now}
    if approver:
        job_fields['cancel_approved_by'] = approver
    Job.objects.filter(booking=booking).update(**job_fields)
    Certificate.objects.filter(job__booking=booking).update(cert_status='revoked', revoke_reason=reason)


@transaction.atomic
def request_cancel(booking_id, *, reason, actor) -> dict:
    """Unpaid bookings (or a manager) cancel at once; paid ones wait for refund review."""
    booking = Booking.objects.select_for_update().filter(pk=booking_id).first()
    if not booking:
        raise ServiceError('ไม่พบรายการจอง', status=404)
    if booking.status == 'cancelled':
        raise ServiceError('รายการนี้ถูกยกเลิกไปแล้ว')
    reason = clean_text(reason, 2000) or 'ลูกค้ายกเลิกการจอง'
    staff_actor = actor if actor and actor.is_authenticated else None
    if is_manager(actor) or booking.payment_status != 'paid':
        _cancel_everything(booking, reason, actor)
        item, _ = CancellationRequest.objects.update_or_create(booking=booking, defaults={
            'reason': reason, 'status': 'approved', 'requested_by': staff_actor, 'reviewed_by': staff_actor,
            'refund_status': 'not_required', 'refund_amount': 0})
        record_event(actor, 'cancel_approved', booking=booking, reason=reason)
        return {'id': item.pk, 'status': 'cancelled', 'message': 'ยกเลิกการจองเรียบร้อยแล้ว'}
    item, _ = CancellationRequest.objects.update_or_create(
        booking=booking, defaults={'reason': reason, 'requested_by': staff_actor, 'status': 'pending'})
    record_event(actor, 'cancel_requested', booking=booking, reason=reason)
    return {'id': item.pk, 'status': 'pending', 'message': 'ส่งคำขอยกเลิกแล้ว รอ Admin ตรวจสอบยอดคืนเงิน'}


@transaction.atomic
def review_cancel(request_id, *, action, refund_amount=0, reference='', actor) -> str:
    item = CancellationRequest.objects.select_for_update().filter(pk=request_id).first()
    if not item:
        raise ServiceError('ไม่พบคำขอยกเลิก', status=404)
    booking = Booking.objects.select_for_update().get(pk=item.booking_id)
    if action == 'refund':
        if item.status != 'approved' or item.refund_status not in ('pending', 'paid_out'):
            raise ServiceError('ยังไม่มีรายการคืนเงินที่อนุมัติ')
        if item.refund_status == 'paid_out':
            return 'paid_out'
        reference = clean_text(reference, 255)
        if not reference:
            raise ServiceError('กรุณาระบุเลขอ้างอิงหลักฐานคืนเงิน')
        item.refund_status, item.refund_reference = 'paid_out', reference
        item.save(update_fields=['refund_status', 'refund_reference'])
        record_event(actor, 'refund_paid_out', booking=booking, reference=reference, amount=item.refund_amount)
        return 'paid_out'
    if item.status != 'pending':
        return item.status
    if action not in ('approve', 'reject'):
        raise ServiceError('คำสั่งไม่ถูกต้อง')
    amount = money(refund_amount or 0)
    maximum = money(booking.total) if booking.payment_status == 'paid' else money(0)
    if amount < 0 or amount > maximum:
        raise ServiceError('ยอดคืนต้องไม่เกินยอดชำระจริง')
    item.status, item.reviewed_by = ('approved' if action == 'approve' else 'rejected'), actor
    if action == 'approve':
        item.refund_amount = amount
        item.refund_status = 'pending' if amount else 'not_required'
        _cancel_everything(booking, item.reason, actor, approver=actor)
    item.save()
    record_event(actor, f'cancel_{action}', booking=booking, refund_amount=amount)
    return item.status

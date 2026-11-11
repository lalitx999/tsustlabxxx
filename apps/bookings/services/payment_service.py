"""Receiving money for a booking: slip review (admin) and counter payment (front desk)."""
from django.db import transaction

from apps.audit.services.audit_service import record_event
from apps.bookings.models import Booking
from apps.bookings.services.booking_service import schedule_payment_email
from apps.core.exceptions import ForbiddenError, ServiceError
from apps.core.money import money
from apps.core.permissions import is_admin
from apps.core.services.promptpay import qr_data_url
from apps.core.utils import clean_text
from apps.inspections.models import Job

COUNTER_METHODS = ('cash', 'credit_card', 'transfer', 'promptpay')


def _locked_booking(booking_id) -> Booking:
    booking = Booking.objects.select_for_update().filter(pk=booking_id).first()
    if not booking:
        raise ServiceError('ไม่พบรายการจอง', status=404)
    return booking


def _confirm(booking: Booking, status: str, method: str | None = None):
    booking.payment_status = status
    if method:
        booking.payment_method = method
    if status == 'paid' and booking.status == 'pending':
        booking.status = 'confirmed'
    booking.save(update_fields=['payment_status', 'payment_method', 'status'])
    job_update = {'payment_status': status}
    if method:
        job_update['payment_method'] = method
    Job.objects.filter(booking=booking).update(**job_update)


@transaction.atomic
def review_slip(booking_id, *, action, reference, amount, actor) -> str:
    """Admin approves/rejects an online transfer slip."""
    booking = _locked_booking(booking_id)
    if booking.status == 'cancelled' or not booking.price_snapshot:
        raise ServiceError('ไม่สามารถรับชำระรายการนี้')
    if booking.payment_status == 'paid':
        return 'paid'
    reference = clean_text(reference, 255)
    if action not in ('approve', 'reject') or not reference:
        raise ServiceError('กรุณาระบุผลและเลขอ้างอิง/เหตุผล')
    if action == 'approve':
        if booking.payment_method not in ('promptpay', 'transfer'):
            raise ServiceError('รายการหน้าร้านให้ใช้บันทึกเงินสด/EDC')
        if money(amount) != money(booking.total):
            raise ServiceError('ยอดที่ตรวจสอบไม่ตรงกับยอดรายการ')
    _confirm(booking, 'paid' if action == 'approve' else 'rejected')
    record_event(actor, f'payment_{action}', booking=booking, reference=reference, amount=booking.total)
    if action == 'approve':
        schedule_payment_email(booking)
    return booking.payment_status


@transaction.atomic
def receive_counter_payment(booking_id, *, method, reference, amount, actor) -> str:
    """Front desk records cash / card / transfer received at the shop."""
    booking = _locked_booking(booking_id)
    if booking.payment_status == 'paid':
        return 'paid'
    reference = clean_text(reference, 255)
    if method not in COUNTER_METHODS or not reference or booking.status == 'cancelled' or not booking.price_snapshot:
        raise ServiceError('เลือกช่องทางรับเงินพร้อมเลขอ้างอิงรายการ')
    if money(amount) != money(booking.total):
        raise ServiceError('ยอดรับชำระไม่ตรง')
    if booking.payment_status == 'pending_review' and not is_admin(actor):
        raise ForbiddenError('รายการแนบสลิปออนไลน์ต้องให้ผู้ดูแลตรวจสอบก่อน')
    _confirm(booking, 'paid', method)
    record_event(actor, 'counter_payment', booking=booking, method=method, reference=reference)
    schedule_payment_email(booking)
    return 'paid'


def booking_qr(booking_id) -> dict:
    booking = Booking.objects.filter(pk=booking_id).only('status', 'payment_status', 'price_snapshot').first()
    if not booking or booking.status == 'cancelled' or booking.payment_status == 'paid' or not booking.price_snapshot:
        raise ServiceError('รายการนี้ไม่อยู่ในสถานะรับชำระ')
    return {'qr_image': qr_data_url(booking.total), 'amount': booking.total}

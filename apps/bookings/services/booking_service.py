"""Create a booking (public website, member portal or front desk).

Ported from the legacy workflows.create_booking with the same rules:
idempotent `request_key`, signed quote for customers, slip required for
online transfer, wallet payment for members, photos for Photo Review.
"""
import datetime
import hashlib
import json
import uuid

from django.core import signing
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import Branch
from apps.audit.services.audit_service import record_event
from apps.bookings.models import Booking, BookingPhoto
from apps.catalog.models import ServiceType
from apps.catalog.services.pricing_service import quote, verify_quote
from apps.catalog.services.promo_service import consume_promo
from apps.core.exceptions import ForbiddenError, ServiceError
from apps.core.money import money
from apps.core.permissions import is_front_desk, is_staff_member
from apps.core.utils import clean_text, decode_image
from apps.customers.models import Customer
from apps.customers.services.credit_service import change_credit
from apps.customers.services.customer_service import find_or_create_customer
from apps.notifications.services.outbox_service import queue_staff_notification

RECEIPT_SALT = 'receipt'
ADDRESS_FIELDS = ('return_address_name', 'return_phone', 'return_address_detail', 'return_subdistrict',
                  'return_district', 'return_province', 'return_postal_code')
CUSTOMER_PAYMENTS = ('shop', 'promptpay', 'wallet', 'transfer')
STAFF_PAYMENTS = ('shop', 'promptpay', 'wallet', 'cash', 'credit_card', 'transfer')
MAX_CUSTOMER_PHOTOS = 20


def resolve_customer(user, data) -> Customer | None:
    """Staff may book for any customer_id; a member books for themself."""
    if is_staff_member(user) and data.get('customer_id'):
        customer = Customer.objects.select_related('membership_level').filter(pk=data['customer_id']).first()
        if not customer:
            raise ServiceError('ไม่พบลูกค้า')
        return customer
    if user and user.is_authenticated:
        return Customer.objects.select_related('membership_level').filter(user=user).first()
    return None


def default_branch(branch_id=None) -> Branch:
    branch = Branch.objects.filter(pk=branch_id, is_active=True).first() if branch_id else None
    branch = branch or Branch.objects.filter(is_active=True).order_by('pk').first() or Branch.objects.order_by('pk').first()
    return branch or Branch.objects.create(name='สาขาหลัก (Head Office)', is_active=True)


def receipt_token(booking: Booking) -> str:
    return signing.dumps({'booking_id': booking.pk, 'request_key': str(booking.request_key)}, salt=RECEIPT_SALT)


def _parse_slot(data):
    try:
        date = datetime.date.fromisoformat(str(data.get('date', '')))
        raw = str(data.get('time_slot', '')).split('-')[0].strip()
        time = datetime.time.fromisoformat(raw + ':00' if len(raw) == 5 else raw)
    except (ValueError, TypeError):
        raise ServiceError('กรุณาระบุวันและเวลานัดหมาย')
    return date, time


def _fingerprint(data) -> str:
    payload = {k: v for k, v in data.items() if k not in ('quote_token', 'photos', 'slip')}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()


@transaction.atomic
def create_booking(user, data: dict) -> dict:
    try:
        key = uuid.UUID(str(data.get('request_key', '')))
    except ValueError:
        raise ServiceError('กรุณาส่งรหัสรายการ request_key')
    front_desk = is_front_desk(user)
    if is_staff_member(user) and not front_desk:
        raise ForbiddenError()
    fingerprint = _fingerprint(data)
    customer = resolve_customer(user, data)
    if customer:
        Customer.objects.select_for_update().filter(pk=customer.pk).first()  # serialise retries

    previous = Booking.objects.filter(request_key=key).first()
    if previous:
        if previous.request_fingerprint != fingerprint:
            raise ServiceError('รหัสรายการนี้บันทึกข้อมูลชุดอื่นแล้ว กรุณาตรวจรายการเดิมก่อนสร้างใหม่')
        if customer and previous.customer_id != customer.pk:
            raise ForbiddenError()
        return {'booking': previous, 'receipt_token': receipt_token(previous), 'created': False}

    snapshot = quote(data, customer, allow_manual_price=front_desk)
    if not front_desk or data.get('quote_token'):
        try:
            verify_quote(data.get('quote_token'), snapshot, customer)
        except ServiceError:
            if not front_desk:
                raise

    if customer is None:
        customer = find_or_create_customer(
            full_name=data.get('customer_name'), phone=data.get('phone'), email=data.get('email'),
            line_id=data.get('line_id'), note=data.get('customer_note', ''), tier=snapshot['member_tier'])

    date, time = _parse_slot(data)
    if date < timezone.localdate() and not is_staff_member(user):
        raise ServiceError('วันนัดหมายต้องไม่เป็นวันที่ผ่านมาแล้ว')
    model_name = clean_text(data.get('model'), 100)
    if not model_name:
        raise ServiceError('กรุณาระบุรุ่นสินค้า')

    shipping = snapshot['delivery_method'] == 'shipping'
    address = {}
    for field in ADDRESS_FIELDS:
        limit = Booking._meta.get_field(field).max_length or 2000
        address[field] = clean_text(data.get(field), limit) if shipping else ''
    if shipping and not all(address.values()):
        raise ServiceError('กรุณากรอกที่อยู่ส่งคืนให้ครบ')

    payment = data.get('payment_method') or 'shop'
    if payment not in (STAFF_PAYMENTS if front_desk else CUSTOMER_PAYMENTS):
        raise ServiceError('ไม่รองรับช่องทางชำระนี้')
    if payment == 'wallet' and not (user and user.is_authenticated):
        raise ForbiddenError('กรุณาเข้าสู่ระบบก่อนใช้เครดิต')
    slip = decode_image(data['slip']) if data.get('slip') and payment in ('promptpay', 'transfer') else None
    if payment in ('promptpay', 'transfer') and slip is None and not front_desk:
        raise ServiceError('กรุณาแนบสลิปชำระเงิน')

    photos = data.get('photos') or []
    if not isinstance(photos, list) or len(photos) > MAX_CUSTOMER_PHOTOS:
        raise ServiceError('แนบภาพได้สูงสุด 20 ภาพ')
    if snapshot['service_package'] == 'photo_review' and not photos:
        raise ServiceError('Photo Review ต้องแนบภาพสินค้า')
    photo_files = [decode_image(p) for p in photos]  # validate all before writing anything

    paid_now = payment == 'wallet' or (front_desk and bool(data.get('mark_paid')))
    payment_status = 'pending_review' if slip else ('paid' if paid_now else 'unpaid')
    service, _ = ServiceType.objects.get_or_create(service_name=snapshot['service_package'],
                                                   defaults={'description': 'Inspection Service', 'price_note': ''})
    promo = consume_promo(snapshot['promo_code'])

    booking = Booking(
        customer=customer, branch=default_branch(data.get('branch_id')), booking_date=date, booking_time=time,
        service_type=service, service_package=snapshot['service_package'], category=snapshot['category'],
        brand_name=snapshot['brand'], model=model_name, note=clean_text(data.get('note'), 2000),
        price_snapshot=snapshot, promo_code=promo, promo_code_str=snapshot['promo_code'],
        delivery_method=snapshot['delivery_method'], shipping_fee=snapshot['shipping_fee'],
        payment_method=payment, request_key=key, request_fingerprint=fingerprint,
        payment_status=payment_status, status='confirmed' if payment_status == 'paid' else 'pending', **address)
    if slip:
        booking.payment_slip.save(slip.name, slip, save=False)
    booking.save()

    BookingPhoto.objects.bulk_create([BookingPhoto(booking=booking, photo_type='customer') for _ in photo_files])
    _attach_photo_files(booking, photo_files)

    if payment == 'wallet':
        change_credit(customer, -money(snapshot['total']), f'booking:{booking.pk}', 'ชำระค่าบริการ', user)
        record_event(user, 'wallet_payment', booking=booking, amount=snapshot['total'])
    elif payment_status == 'paid':
        record_event(user, 'counter_payment', booking=booking, method=payment, amount=snapshot['total'],
                     reference=clean_text(data.get('reference'), 120))
    if payment_status == 'paid':
        schedule_payment_email(booking)

    queue_staff_notification(f'booking:{booking.pk}:created', 'booking_created', {'booking_id': booking.pk},
                             channels=('line',))
    from apps.notifications.tasks import notify_line_new_booking
    transaction.on_commit(lambda: notify_line_new_booking.delay(booking.pk))
    return {'booking': booking, 'receipt_token': receipt_token(booking), 'created': True}


def _attach_photo_files(booking, files):
    """bulk_create cannot save files, so store them on the created rows."""
    if not files:
        return
    rows = list(BookingPhoto.objects.filter(booking=booking, photo_type='customer', photo='').order_by('pk'))
    for row, content in zip(rows, files):
        row.photo.save(content.name, content, save=False)
    BookingPhoto.objects.bulk_update(rows, ['photo'])


def schedule_payment_email(booking: Booking) -> None:
    """E-mail only after the payment commits; failures never undo the payment."""
    from apps.notifications.tasks import send_payment_confirmation_email
    transaction.on_commit(lambda: send_payment_confirmation_email.delay(booking.pk))


def read_receipt(token) -> dict:
    """Public receipt by signed link. Never exposes customer details."""
    try:
        signed = signing.loads(token, salt=RECEIPT_SALT, max_age=180 * 86400)
    except (signing.BadSignature, TypeError):
        raise ForbiddenError('ลิงก์ไม่ถูกต้องหรือหมดอายุ กรุณาติดต่อเจ้าหน้าที่')
    booking = (Booking.objects.select_related('job')
               .filter(pk=signed['booking_id'], request_key=signed['request_key']).first())
    if not booking:
        raise ServiceError('ไม่พบรายการ', status=404)
    job = getattr(booking, 'job', None)
    return {
        'booking_id': booking.display_id,
        'status': booking.status,
        'payment_status': booking.payment_status,
        'payment_status_label': booking.payment_status_label,
        'service_package': booking.service_package,
        'booking_date': booking.booking_date.isoformat(),
        'booking_time': booking.booking_time.strftime('%H:%M'),
        'result': job.result if job and job.status == 'completed' else None,
        'total': booking.total,
        'shipping_status': job.shipping_status if job else None,
    }

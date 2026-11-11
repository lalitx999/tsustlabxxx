"""Walk-in counter: one transaction = booking + check-in (+ optional payment)."""
from django.db import transaction
from django.utils import timezone

from apps.bookings.models import Booking
from apps.bookings.services.booking_service import create_booking
from apps.bookings.services.payment_service import receive_counter_payment
from apps.catalog.services.pricing_service import quote
from apps.core.exceptions import ServiceError
from apps.core.utils import clean_text, digits_only, parse_pk
from apps.inspections.models import Job
from apps.inspections.services.job_service import apply_item_details, check_in

ADDRESS_FIELDS = ('return_address_name', 'return_phone', 'return_address_detail', 'return_subdistrict',
                  'return_district', 'return_province', 'return_postal_code')


@transaction.atomic
def create_walkin(data: dict, actor) -> Booking:
    now = timezone.localtime()
    # Payment is recorded below via the counter-payment path so the real method
    # (cash/card/transfer) is stored and counted in revenue reports.
    payload = {**data, 'date': now.date().isoformat(), 'time_slot': now.strftime('%H:%M'),
               'payment_method': 'shop', 'mark_paid': False}
    booking = create_booking(actor, payload)['booking']
    Booking.objects.filter(pk=booking.pk).update(channel='walk_in')
    check_in(booking.pk, data, actor)
    if data.get('mark_paid') is True:
        receive_counter_payment(booking.pk, method=data.get('counter_method') or 'cash',
                                reference=data.get('reference') or f'WALKIN-{booking.pk}',
                                amount=booking.total, actor=actor)
    return booking


@transaction.atomic
def update_walkin(booking_id, data: dict, actor) -> Booking:
    """Edit customer/item/package. Unpaid bookings are re-priced; paid prices never change."""
    booking = (Booking.objects.select_for_update(of=('self',)).select_related('customer__membership_level')
               .filter(pk=parse_pk(booking_id)).first())
    if not booking:
        raise ServiceError('ไม่พบรายการ', status=404)
    if booking.status == 'cancelled':
        raise ServiceError('รายการนี้ถูกยกเลิกแล้ว')

    customer = booking.customer
    if data.get('customer_name'):
        customer.full_name = clean_text(data['customer_name'], 255)
    if data.get('customer_phone'):
        customer.phone_number = digits_only(data['customer_phone'])
    if 'customer_email' in data:
        customer.email = clean_text(data['customer_email'], 254) or None
    customer.save(update_fields=['full_name', 'phone_number', 'email'])

    reprice = False
    for field, attr in (('brand', 'brand_name'), ('model', 'model'), ('category', 'category'), ('note', 'note')):
        if field in data and data[field] is not None:
            setattr(booking, attr, clean_text(data[field], 2000 if field == 'note' else 100))
            reprice = reprice or field in ('brand', 'category')
    if data.get('service_package') in ('cert_15d', 'cert_90d', 'photo_review') \
            and data['service_package'] != booking.service_package:
        booking.service_package, reprice = data['service_package'], True
    if data.get('delivery_method') in ('self_pickup', 'shipping') and data['delivery_method'] != booking.delivery_method:
        booking.delivery_method, reprice = data['delivery_method'], True
    for field in ADDRESS_FIELDS:
        if field in data:
            setattr(booking, field, clean_text(data[field], Booking._meta.get_field(field).max_length or 2000))

    manual = str(data.get('manual_service_amount') or '').strip()
    if booking.payment_status != 'paid' and (reprice or manual):
        snapshot = quote({
            'service_package': booking.service_package, 'category': booking.category, 'brand': booking.brand_name,
            'delivery_method': booking.delivery_method, 'membership_level': customer.tier_name.lower(),
            'promo_code': booking.promo_code_str,
            'manual_service_amount': manual or None, 'price_reason': data.get('price_reason', ''),
        }, customer, allow_manual_price=True)
        booking.price_snapshot = snapshot
        booking.shipping_fee = snapshot['shipping_fee']
    booking.save()

    job = Job.objects.select_for_update().filter(booking=booking).first()
    if job:
        apply_item_details(job, data)
        job.service_package = booking.service_package
        if booking.payment_status != 'paid':
            job.price_snapshot = booking.price_snapshot
            job.price = booking.price_snapshot.get('total', job.price)
            job.vat_amount = booking.price_snapshot.get('vat_amount', job.vat_amount)
        if booking.delivery_method == 'shipping' and job.shipping_status == 'not_applicable':
            job.shipping_status = 'pending_return'
        elif booking.delivery_method == 'self_pickup' and job.shipping_status == 'pending_return':
            job.shipping_status = 'not_applicable'
        job.save()
    else:
        check_in(booking.pk, data, actor)
    return booking

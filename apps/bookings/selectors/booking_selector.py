"""Read-side queries for bookings (always select_related to avoid N+1)."""
import datetime

from django.db.models import Q

from apps.bookings.models import Booking, CancellationRequest

LIST_RELATED = ('customer__membership_level', 'branch', 'job', 'cancellationrequest')


def booking_list(*, status=None, date=None, query=None, payment_status=None, limit=200):
    queryset = Booking.objects.select_related(*LIST_RELATED).order_by('-created_at')
    if status:
        queryset = queryset.filter(status=status)
    if payment_status:
        queryset = queryset.filter(payment_status=payment_status)
    if date:
        queryset = queryset.filter(Q(booking_date=date) | Q(created_at__date=date))
    if query:
        query = query.strip()
        q = Q(customer__full_name__icontains=query) | Q(customer__phone_number__contains=query) | \
            Q(brand_name__icontains=query) | Q(model__icontains=query)
        if query.upper().startswith('BK-') or query.isdigit():
            try:
                q |= Q(pk=int(query.upper().replace('BK-', '')))
            except ValueError:
                pass
        queryset = queryset.filter(q)
    return queryset[:limit]


def bookings_for_day(day: datetime.date):
    return (Booking.objects.select_related(*LIST_RELATED)
            .filter(Q(booking_date=day) | Q(created_at__date=day)).order_by('booking_time', '-pk'))


def booking_detail(booking_id):
    return (Booking.objects.select_related(*LIST_RELATED, 'service_type', 'promo_code')
            .prefetch_related('photos').filter(pk=booking_id).first())


def bookings_for_customer(customer):
    return (Booking.objects.select_related('job', 'job__certificate')
            .filter(customer=customer).order_by('-booking_date', '-booking_time'))


def photo_urls(booking) -> dict:
    grouped = {'customer': [], 'staff': []}
    for photo in booking.photos.all():
        if photo.photo:
            grouped[photo.photo_type].append({'id': photo.pk, 'url': photo.photo.url})
    return grouped


def pending_cancellations(limit=200):
    return (CancellationRequest.objects.select_related('booking__customer', 'requested_by')
            .filter(Q(status='pending') | Q(refund_status='pending')).order_by('-created_at')[:limit])


def pending_slip_reviews():
    return (Booking.objects.select_related('customer').filter(payment_status='pending_review')
            .exclude(status='cancelled').order_by('created_at'))


def serialize_booking(b: Booking) -> dict:
    job = getattr(b, 'job', None)
    cancel = getattr(b, 'cancellationrequest', None)
    return {
        'id': b.pk,
        'display_id': b.display_id,
        'customer_id': b.customer_id,
        'customer_name': b.customer.full_name,
        'customer_phone': b.customer.phone_number,
        'customer_email': b.customer.email or '',
        'member_tier': b.customer.tier_name,
        'branch': b.branch.name,
        'booking_date': b.booking_date.isoformat(),
        'booking_time': b.booking_time.strftime('%H:%M'),
        'category': b.category,
        'brand_name': b.brand_name,
        'model': b.model,
        'note': b.note,
        'status': b.status,
        'service_package': b.service_package,
        'channel': b.channel,
        'payment_status': b.payment_status,
        'payment_status_label': b.payment_status_label,
        'payment_method': b.payment_method,
        'delivery_method': b.delivery_method,
        'total': b.total,
        'quote': b.price_snapshot,
        'has_slip': bool(b.payment_slip or b.payment_evidence),
        'job_id': job.pk if job else None,
        'job_display_id': job.display_id if job else '',
        'job_status': job.status if job else '',
        'cancellation': {'id': cancel.pk, 'status': cancel.status, 'reason': cancel.reason,
                         'refund_status': cancel.refund_status, 'refund_amount': str(cancel.refund_amount)}
        if cancel else None,
        'created_at': b.created_at.isoformat(),
    }

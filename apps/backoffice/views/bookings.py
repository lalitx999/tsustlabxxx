"""Walk-in counter and booking management."""
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST

from apps.bookings.selectors import booking_selector, tax_document_selector
from apps.bookings.services import cancellation_service, payment_service
from apps.catalog.models import CATEGORIES
from apps.catalog.selectors.catalog_selector import brand_names, enabled_packages
from apps.catalog.services.pricing_service import quote
from apps.core.decorators import ajax_view, reply, role_required
from apps.core.exceptions import ServiceError
from apps.core.permissions import ADMIN_ROLES, FRONT_DESK_ROLES
from apps.core.utils import parse_pk
from apps.customers.selectors.customer_selector import customer_by_phone, serialize_customer
from apps.inspections.services import job_service, walkin_service
from apps.website.content import CATEGORY_LABELS, DEFAULT_BRANDS


@role_required(*FRONT_DESK_ROLES)
@require_GET
def walkin(request):
    return render(request, 'backoffice/walkin.html', {
        'title': 'Walk-in (New Sale)', 'packages': enabled_packages(),
        'categories': [(code, CATEGORY_LABELS[code][0]) for code in CATEGORIES],
        'brands': brand_names() or DEFAULT_BRANDS,
    })


@role_required(*FRONT_DESK_ROLES)
@require_GET
@ajax_view
def customer_lookup(request):
    customer = customer_by_phone(''.join(c for c in request.GET.get('phone', '') if c.isdigit()))
    return serialize_customer(customer) if customer else None


@role_required(*FRONT_DESK_ROLES)
@require_POST
@ajax_view
def walkin_quote(request):
    customer = customer_by_phone(''.join(c for c in str(request.json.get('phone', '')) if c.isdigit()))
    return quote(request.json, customer, allow_manual_price=True)


@role_required(*FRONT_DESK_ROLES)
@require_POST
@ajax_view
def walkin_create(request):
    booking = walkin_service.create_walkin(request.json, request.user)
    detail = booking_selector.booking_detail(booking.pk)
    return reply(booking_selector.serialize_booking(detail), message='บันทึกรายการและออกคิวเรียบร้อยแล้ว', status=201)


@role_required(*FRONT_DESK_ROLES)
@require_POST
@ajax_view
def walkin_update(request, pk):
    walkin_service.update_walkin(pk, request.json, request.user)
    return reply(booking_selector.serialize_booking(booking_selector.booking_detail(pk)), message='บันทึกการแก้ไขแล้ว')


@role_required(*FRONT_DESK_ROLES)
@require_GET
def bookings(request):
    return render(request, 'backoffice/bookings.html', {'title': 'Booking'})


@role_required(*FRONT_DESK_ROLES)
@require_GET
@ajax_view
def booking_rows(request):
    rows = booking_selector.booking_list(
        status=request.GET.get('status') or None, date=request.GET.get('date') or None,
        query=request.GET.get('q') or None, payment_status=request.GET.get('payment') or None)
    return [booking_selector.serialize_booking(b) for b in rows]


@role_required(*FRONT_DESK_ROLES)
@require_GET
@ajax_view
def booking_get(request, pk):
    booking = booking_selector.booking_detail(parse_pk(pk))
    if not booking:
        raise ServiceError('ไม่พบรายการ', status=404)
    data = booking_selector.serialize_booking(booking)
    data['photos'] = booking_selector.photo_urls(booking)
    data['slip_url'] = booking.payment_slip.url if booking.payment_slip else ''
    data['legacy_slip'] = booking.payment_evidence if booking.payment_evidence.startswith('data:image') else ''
    data['documents'] = [dict(tax_document_selector.serialize_document(d),
                              print_url=reverse('backoffice:document_print', args=[d.pk]))
                         for d in tax_document_selector.documents_for_booking(booking.pk)]
    data['intake_url'] = reverse('backoffice:intake_print', args=[booking.pk])
    return data


@role_required(*FRONT_DESK_ROLES)
@require_POST
@ajax_view
def booking_check_in(request, pk):
    job = job_service.check_in(pk, request.json, request.user)
    return reply({'job_id': job.pk, 'queue_no': job.queue_no}, message=f'รับงานแล้ว คิว {job.queue_no}')


@role_required(*FRONT_DESK_ROLES)
@require_POST
@ajax_view
def booking_counter_payment(request, pk):
    data = request.json
    status = payment_service.receive_counter_payment(
        parse_pk(pk), method=data.get('method'), reference=data.get('reference'), amount=data.get('amount'),
        actor=request.user)
    return reply({'status': status}, message='บันทึกรับชำระเงินแล้ว')


@role_required(*FRONT_DESK_ROLES)
@require_POST
@ajax_view
def booking_qr(request, pk):
    return payment_service.booking_qr(parse_pk(pk))


@role_required(*ADMIN_ROLES)
@require_POST
@ajax_view
def booking_slip_review(request, pk):
    data = request.json
    status = payment_service.review_slip(parse_pk(pk), action=data.get('action'), reference=data.get('reference'),
                                         amount=data.get('amount'), actor=request.user)
    return reply({'status': status}, message='บันทึกผลตรวจสลิปแล้ว')


@role_required(*FRONT_DESK_ROLES)
@require_POST
@ajax_view
def booking_cancel(request, pk):
    result = cancellation_service.request_cancel(parse_pk(pk), reason=request.json.get('reason'), actor=request.user)
    return reply(result, message=result['message'])


@role_required(*FRONT_DESK_ROLES)
@require_POST
@ajax_view
def cancellation_review(request, pk):
    data = request.json
    status = cancellation_service.review_cancel(pk, action=data.get('action'), refund_amount=data.get('refund_amount'),
                                                reference=data.get('reference'), actor=request.user)
    return reply({'status': status}, message='บันทึกแล้ว')

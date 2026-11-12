"""Receipts (80mm slip) and full tax invoices (A4) for paid bookings.

Each document gets a running number per month (RC-2611-0001, INV-2611-0001) and keeps a copy of the
buyer details and amounts, so a reprint always shows exactly what was issued.
"""
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.audit.services.audit_service import record_event
from apps.bookings.models import Booking, TaxDocument
from apps.core.exceptions import ForbiddenError, ServiceError
from apps.core.money import money
from apps.core.permissions import is_admin
from apps.core.utils import clean_text, digits_only

# Which payment states allow which document.
ALLOWED_PAYMENT = {
    TaxDocument.RECEIPT: ('paid',),
    TaxDocument.TAX_INVOICE: ('paid', 'invoiced'),
}


def amounts_from_snapshot(snapshot: dict) -> dict:
    """Turn a booking price snapshot into the figures printed on the document."""
    snap = snapshot or {}
    total = money(snap.get('total') or 0)
    service = money(snap.get('service_amount') or total)
    before = money(snap.get('service_amount_before_discount') or service)
    discount = money(before - service) if before > service else money(0)
    shipping = money(snap.get('shipping_fee') or 0)
    vat = money(snap.get('vat_amount') or 0)
    lines = [{'name': 'บริการตรวจสอบสินค้า', 'quantity': 1, 'price': str(before),
              'discount': str(discount), 'amount': str(service)}]
    if shipping > 0:
        lines.append({'name': 'ค่าจัดส่งสินค้าคืน', 'quantity': 1, 'price': str(shipping),
                      'discount': '0.00', 'amount': str(shipping)})
    return {
        'lines': lines,
        'gross': str(money(before + shipping)),
        'discount': str(discount),
        'after_discount': str(money(service + shipping)),
        'vat': str(vat),
        'before_vat': str(money(total - vat)),
        'total': str(total),
        'prices_include_vat': bool(snap.get('prices_include_vat', True)),
    }


def _buyer(booking: Booking, data: dict) -> dict:
    customer = booking.customer
    tax_id = digits_only(data.get('buyer_tax_id'))
    if tax_id and len(tax_id) != 13:
        raise ServiceError('เลขประจำตัวผู้เสียภาษีต้องมี 13 หลัก')
    address = clean_text(data.get('buyer_address'), 500)
    if not address and booking.return_address_detail:
        address = ' '.join(filter(None, [booking.return_address_detail, booking.return_subdistrict,
                                         booking.return_district, booking.return_province,
                                         booking.return_postal_code]))
    return {
        'buyer_name': clean_text(data.get('buyer_name'), 255) or customer.full_name,
        'buyer_tax_id': tax_id,
        'buyer_branch': clean_text(data.get('buyer_branch'), 100) or ('สำนักงานใหญ่' if tax_id else ''),
        'buyer_address': address,
    }


def _next_number(doc_type: str) -> str:
    prefix = f"{TaxDocument.PREFIX[doc_type]}-{timezone.localdate():%y%m}-"
    last = (TaxDocument.objects.filter(number__startswith=prefix).order_by('-number')
            .values_list('number', flat=True).first())
    seq = int(last.rsplit('-', 1)[1]) + 1 if last else 1
    return f'{prefix}{seq:04d}'


def issue(booking_id, doc_type: str, data: dict, actor) -> tuple[TaxDocument, bool]:
    """Return (document, created). An existing active document of the same type is reused as-is."""
    if doc_type not in TaxDocument.PREFIX:
        raise ServiceError('ประเภทเอกสารไม่ถูกต้อง')
    for attempt in range(5):
        try:
            return _issue_once(booking_id, doc_type, data or {}, actor)
        except IntegrityError:
            # Two counters issued at the same moment and picked the same number: try the next one.
            if attempt == 4:
                raise ServiceError('ออกเลขเอกสารไม่สำเร็จ กรุณาลองใหม่อีกครั้ง')
    raise AssertionError('unreachable')


@transaction.atomic
def _issue_once(booking_id, doc_type, data, actor):
    booking = (Booking.objects.select_for_update(of=('self',)).select_related('customer')
               .filter(pk=booking_id).first())
    if not booking:
        raise ServiceError('ไม่พบรายการ', status=404)
    existing = booking.tax_documents.filter(doc_type=doc_type, voided_at__isnull=True).first()
    if existing:
        return existing, False
    if booking.status == 'cancelled':
        raise ServiceError('รายการนี้ถูกยกเลิกแล้ว ออกเอกสารไม่ได้')
    if booking.payment_status not in ALLOWED_PAYMENT[doc_type]:
        raise ServiceError('ต้องรับชำระเงินก่อน จึงออกใบเสร็จ / ใบกำกับภาษีได้')
    buyer = _buyer(booking, data)
    if doc_type == TaxDocument.TAX_INVOICE and not buyer['buyer_address']:
        raise ServiceError('กรุณากรอกที่อยู่สำหรับออกใบกำกับภาษี')
    with transaction.atomic():
        document = TaxDocument.objects.create(
            booking=booking, doc_type=doc_type, number=_next_number(doc_type),
            amounts=amounts_from_snapshot(booking.price_snapshot), issued_by=actor, **buyer)
    record_event(actor, 'tax_document_issued', booking=booking, number=document.number, doc_type=doc_type)
    return document, True


@transaction.atomic
def void(document_id, reason, actor) -> TaxDocument:
    """Admin cancels a document (e.g. wrong tax ID) so a new one can be issued. The number is never reused."""
    if not is_admin(actor):
        raise ForbiddenError()
    reason = clean_text(reason, 500)
    if not reason:
        raise ServiceError('กรุณาระบุเหตุผลการยกเลิกเอกสาร')
    document = TaxDocument.objects.select_for_update().filter(pk=document_id).first()
    if not document:
        raise ServiceError('ไม่พบเอกสาร', status=404)
    if document.voided_at:
        raise ServiceError('เอกสารนี้ถูกยกเลิกไปแล้ว')
    document.voided_at = timezone.now()
    document.voided_by = actor
    document.void_reason = reason
    document.save(update_fields=['voided_at', 'voided_by', 'void_reason'])
    record_event(actor, 'tax_document_voided', booking=document.booking, number=document.number, reason=reason)
    return document

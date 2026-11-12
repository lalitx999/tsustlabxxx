"""Read-side queries for receipts and tax invoices."""
from django.conf import settings

from apps.bookings.models import TaxDocument
from apps.core.thai_text import baht_text

PAYMENT_LABELS = {'cash': 'เงินสด', 'credit_card': 'บัตรเครดิต', 'transfer': 'โอนเงิน',
                  'promptpay': 'PromptPay QR', 'wallet': 'เครดิตสมาชิก', 'shop': 'ชำระที่ร้าน',
                  'postpaid': 'วางบิล'}


def documents_for_booking(booking_id):
    return (TaxDocument.objects.filter(booking_id=booking_id).select_related('issued_by')
            .only('id', 'doc_type', 'number', 'issued_at', 'voided_at', 'void_reason', 'booking_id',
                  'issued_by__username')
            .order_by('-issued_at'))


def serialize_document(doc: TaxDocument) -> dict:
    return {'id': doc.pk, 'doc_type': doc.doc_type, 'label': doc.get_doc_type_display(), 'number': doc.number,
            'issued_at': doc.issued_at.isoformat(), 'issued_by': doc.issued_by.username if doc.issued_by else '',
            'voided': bool(doc.voided_at), 'void_reason': doc.void_reason}


def document_for_print(document_id):
    return (TaxDocument.objects
            .select_related('booking__customer', 'booking__job', 'issued_by')
            .filter(pk=document_id).first())


def print_context(doc: TaxDocument) -> dict:
    booking = doc.booking
    job = getattr(booking, 'job', None)
    issued_by = doc.issued_by
    return {
        'doc': doc, 'booking': booking, 'job': job, 'amounts': doc.amounts,
        'sets': [{'th': 'ต้นฉบับ', 'en': 'ORIGINAL'}, {'th': 'คู่ฉบับ', 'en': 'COPY'}],
        'baht_text': baht_text(doc.amounts.get('total', 0)),
        'payment_label': PAYMENT_LABELS.get(booking.payment_method, booking.payment_method or '-'),
        'seller': (issued_by.get_full_name() or issued_by.username) if issued_by else 'Trust Lab',
        'company': {'name': settings.COMPANY_NAME, 'line1': settings.COMPANY_ADDRESS_LINE1,
                    'line2': settings.COMPANY_ADDRESS_LINE2, 'tax_id': settings.COMPANY_TAX_ID,
                    'phone': settings.COMPANY_PHONE},
        'product': ' '.join(filter(None, [job.brand if job else booking.brand_name,
                                          job.model if job else booking.model])),
    }

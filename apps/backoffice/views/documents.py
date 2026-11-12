"""Receipts, tax invoices and the walk-in intake slip (print pages opened in a new tab)."""
from django.conf import settings
from django.http import Http404
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST

from apps.bookings.selectors import booking_selector, tax_document_selector
from apps.bookings.services import tax_document_service
from apps.core.decorators import ajax_view, reply, role_required
from apps.core.permissions import ADMIN_ROLES, FRONT_DESK_ROLES
from apps.core.utils import parse_pk

TEMPLATES = {'receipt': 'backoffice/print/receipt_slip.html', 'tax_invoice': 'backoffice/print/tax_invoice.html'}


@role_required(*FRONT_DESK_ROLES)
@require_POST
@ajax_view
def document_issue(request, pk):
    data = request.json
    document, created = tax_document_service.issue(parse_pk(pk), data.get('doc_type'), data, request.user)
    payload = tax_document_selector.serialize_document(document)
    payload['print_url'] = reverse('backoffice:document_print', args=[document.pk])
    message = f'ออกเอกสาร {document.number} แล้ว' if created else f'พิมพ์ซ้ำเอกสารเดิม {document.number}'
    return reply(payload, message=message, status=201 if created else 200)


@role_required(*FRONT_DESK_ROLES)
@require_GET
def document_print(request, pk):
    document = tax_document_selector.document_for_print(pk)
    if not document:
        raise Http404
    context = tax_document_selector.print_context(document)
    context['autoprint'] = request.GET.get('autoprint') == '1'
    return render(request, TEMPLATES[document.doc_type], context)


@role_required(*ADMIN_ROLES)
@require_POST
@ajax_view
def document_void(request, pk):
    document = tax_document_service.void(pk, request.json.get('reason'), request.user)
    return reply(tax_document_selector.serialize_document(document), message=f'ยกเลิกเอกสาร {document.number} แล้ว')


@role_required(*FRONT_DESK_ROLES)
@require_GET
def intake_print(request, pk):
    booking = booking_selector.booking_detail(pk)
    if not booking:
        raise Http404
    return render(request, 'backoffice/print/intake_slip.html', {
        'booking': booking, 'job': getattr(booking, 'job', None),
        'payment_label': tax_document_selector.PAYMENT_LABELS.get(booking.payment_method, booking.payment_method),
        'company_phone': settings.COMPANY_PHONE, 'autoprint': request.GET.get('autoprint') == '1',
    })

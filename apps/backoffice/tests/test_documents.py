"""Receipts, tax invoices and the intake slip (phase 2.5 / 2.6)."""
from decimal import Decimal

from django.test import SimpleTestCase
from django.utils import timezone

from apps.audit.models import WorkflowEvent
from apps.bookings.models import TaxDocument
from apps.bookings.services.tax_document_service import amounts_from_snapshot
from apps.core.thai_text import baht_text

from .base import BackofficeTestCase, bo

SHIP = {'delivery_method': 'shipping', 'return_address_name': 'Somchai', 'return_phone': '0812345678',
        'return_address_detail': '1 Rama 1 Rd', 'return_subdistrict': 'Pathum Wan', 'return_district': 'Pathum Wan',
        'return_province': 'Bangkok', 'return_postal_code': '10330'}


class BahtTextTests(SimpleTestCase):
    def test_amounts_in_words(self):
        cases = {
            '0': 'ศูนย์บาทถ้วน',
            '1': 'หนึ่งบาทถ้วน',
            '11': 'สิบเอ็ดบาทถ้วน',
            '21': 'ยี่สิบเอ็ดบาทถ้วน',
            '101': 'หนึ่งร้อยเอ็ดบาทถ้วน',
            '3000': 'สามพันบาทถ้วน',
            '3210.00': 'สามพันสองร้อยสิบบาทถ้วน',
            '1250.50': 'หนึ่งพันสองร้อยห้าสิบบาทห้าสิบสตางค์',
            '1000000': 'หนึ่งล้านบาทถ้วน',
            '1000001': 'หนึ่งล้านเอ็ดบาทถ้วน',
            '21000000': 'ยี่สิบเอ็ดล้านบาทถ้วน',
            '0.25': 'ศูนย์บาทยี่สิบห้าสตางค์',
            '-5': 'ลบห้าบาทถ้วน',
        }
        for amount, words in cases.items():
            with self.subTest(amount=amount):
                self.assertEqual(baht_text(amount), words)

    def test_amounts_from_snapshot_adds_shipping_line(self):
        amounts = amounts_from_snapshot({'service_amount_before_discount': '3000.00', 'service_amount': '2550.00',
                                         'shipping_fee': '100.00', 'vat_amount': '173.36', 'total': '2650.00'})
        self.assertEqual(len(amounts['lines']), 2)
        self.assertEqual((amounts['gross'], amounts['discount'], amounts['after_discount']),
                         ('3100.00', '450.00', '2650.00'))
        self.assertEqual(amounts['before_vat'], '2476.64')


class IssueDocumentTests(BackofficeTestCase):
    def issue(self, booking, doc_type, role='front', **buyer):
        self.login(role)
        return self.post(bo('document_issue', booking.pk), {'doc_type': doc_type, **buyer})

    def test_unpaid_booking_cannot_get_a_receipt(self):
        booking, _ = self.walkin()
        res = self.issue(booking, 'receipt')
        self.assertEqual(res.status_code, 400)
        self.assertIn('ต้องรับชำระเงินก่อน', res.json()['message'])
        self.assertFalse(TaxDocument.objects.exists())

    def test_receipt_number_is_fixed_and_reprint_reuses_it(self):
        booking, _ = self.walkin(mark_paid=True, reference='R')
        first = self.ok(self.issue(booking, 'receipt'), 201)['data']
        prefix = f'RC-{timezone.localdate():%y%m}-'
        self.assertEqual(first['number'], prefix + '0001')
        again = self.ok(self.issue(booking, 'receipt'), 200)['data']
        self.assertEqual(again['id'], first['id'])
        self.assertEqual(TaxDocument.objects.count(), 1)
        # A second paid booking gets the next number.
        other, _ = self.walkin(mark_paid=True, reference='R2', phone='0899999992')
        self.assertEqual(self.ok(self.issue(other, 'receipt'), 201)['data']['number'], prefix + '0002')
        self.assertTrue(WorkflowEvent.objects.filter(action='tax_document_issued', booking=booking).exists())

    def test_receipt_and_invoice_numbers_run_separately(self):
        booking, _ = self.walkin(mark_paid=True, reference='R', **SHIP)
        receipt = self.ok(self.issue(booking, 'receipt'), 201)['data']
        invoice = self.ok(self.issue(booking, 'tax_invoice'), 201)['data']
        self.assertTrue(receipt['number'].startswith('RC-') and receipt['number'].endswith('-0001'))
        self.assertTrue(invoice['number'].startswith('INV-') and invoice['number'].endswith('-0001'))

    def test_tax_invoice_keeps_buyer_details_and_amounts(self):
        booking, _ = self.walkin(mark_paid=True, reference='R', **SHIP)
        data = self.ok(self.issue(booking, 'tax_invoice', buyer_name='ACME Co., Ltd.',
                                  buyer_tax_id='0105-56915-0000', buyer_address='99 Silom Bangkok'), 201)['data']
        doc = TaxDocument.objects.get(pk=data['id'])
        self.assertEqual((doc.buyer_name, doc.buyer_tax_id, doc.buyer_branch, doc.buyer_address),
                         ('ACME Co., Ltd.', '0105569150000', 'สำนักงานใหญ่', '99 Silom Bangkok'))
        self.assertEqual(doc.amounts['total'], booking.total)
        self.assertEqual(len(doc.amounts['lines']), 2)  # service + return shipping
        # Later price edits do not change an issued document.
        booking.price_snapshot = dict(booking.price_snapshot, total='1.00')
        booking.save(update_fields=['price_snapshot'])
        page = self.client.get(bo('document_print', doc.pk))
        self.assertContains(page, 'ACME Co., Ltd.')
        self.assertContains(page, doc.number)
        self.assertContains(page, 'ต้นฉบับ')
        self.assertContains(page, 'คู่ฉบับ')
        self.assertContains(page, f'{Decimal(doc.amounts["total"]):,.2f}')
        self.assertNotContains(page, 'fonts.googleapis.com')

    def test_tax_invoice_defaults_to_customer_and_return_address(self):
        booking, _ = self.walkin(mark_paid=True, reference='R', **SHIP)
        doc = TaxDocument.objects.get(pk=self.ok(self.issue(booking, 'tax_invoice'), 201)['data']['id'])
        self.assertEqual(doc.buyer_name, booking.customer.full_name)
        self.assertIn('1 Rama 1 Rd', doc.buyer_address)
        self.assertEqual(doc.buyer_branch, '')

    def test_tax_invoice_needs_an_address_and_valid_tax_id(self):
        booking, _ = self.walkin(mark_paid=True, reference='R')
        self.assertIn('ที่อยู่', self.issue(booking, 'tax_invoice').json()['message'])
        res = self.issue(booking, 'tax_invoice', buyer_tax_id='123', buyer_address='x')
        self.assertIn('13 หลัก', res.json()['message'])
        self.assertEqual(self.issue(booking, 'nonsense').status_code, 400)

    def test_cancelled_booking_cannot_get_a_new_document(self):
        booking, _ = self.walkin(mark_paid=True, reference='R')
        booking.status = 'cancelled'
        booking.save(update_fields=['status'])
        self.assertEqual(self.issue(booking, 'receipt').status_code, 400)

    def test_void_is_admin_only_and_allows_reissue_with_a_new_number(self):
        booking, _ = self.walkin(mark_paid=True, reference='R')
        first = self.ok(self.issue(booking, 'receipt'), 201)['data']
        self.login('front')
        self.assertEqual(self.post(bo('document_void', first['id']), {'reason': 'typo'}).status_code, 403)
        self.login('admin')
        self.assertEqual(self.post(bo('document_void', first['id']), {}).status_code, 400)  # reason required
        self.ok(self.post(bo('document_void', first['id']), {'reason': 'เลขผู้เสียภาษีผิด'}))
        self.assertEqual(self.post(bo('document_void', first['id']), {'reason': 'again'}).status_code, 400)
        second = self.ok(self.issue(booking, 'receipt'), 201)['data']
        self.assertNotEqual(second['number'], first['number'])
        self.assertContains(self.client.get(bo('document_print', first['id'])), 'ถูกยกเลิกแล้ว')

    def test_booking_detail_lists_documents(self):
        booking, _ = self.walkin(mark_paid=True, reference='R')
        self.ok(self.issue(booking, 'receipt'), 201)
        data = self.ok(self.get_json(bo('booking_get', booking.pk)))['data']
        self.assertEqual(len(data['documents']), 1)
        self.assertTrue(data['documents'][0]['print_url'].endswith('/print/'))
        self.assertTrue(data['intake_url'].endswith('/intake-slip/'))

    def test_print_pages_need_staff(self):
        booking, _ = self.walkin(mark_paid=True, reference='R')
        doc_id = self.ok(self.issue(booking, 'receipt'), 201)['data']['id']
        for role in (None, 'customer'):
            self.login(role)
            for url in (bo('document_print', doc_id), bo('intake_print', booking.pk)):
                with self.subTest(role=role, url=url):
                    self.assertNotEqual(self.client.get(url).status_code, 200)
            self.assertIn(self.post(bo('document_issue', booking.pk), {'doc_type': 'receipt'}).status_code,
                          (302, 401, 403))
        self.login('front')
        receipt = self.client.get(bo('document_print', doc_id) + '?autoprint=1')
        self.assertContains(receipt, 'ใบกำกับภาษีอย่างย่อ')
        self.assertContains(receipt, 'window.print()')
        intake = self.client.get(bo('intake_print', booking.pk))
        self.assertContains(intake, 'ใบรับสินค้า')
        self.assertContains(intake, booking.customer.full_name)
        self.assertEqual(self.client.get(bo('document_print', 99999)).status_code, 404)

    def test_document_list_query_count_is_flat(self):
        from apps.bookings.selectors.tax_document_selector import documents_for_booking, serialize_document
        booking, _ = self.walkin(mark_paid=True, reference='R', **SHIP)
        self.ok(self.issue(booking, 'receipt'), 201)
        self.ok(self.issue(booking, 'tax_invoice'), 201)
        with self.assertNumQueries(1):
            [serialize_document(d) for d in documents_for_booking(booking.pk)]

"""Customer display (/pos-display/) and the Walk-in counter flow that feeds it (phase 2.2)."""
from django.test import override_settings
from django.urls import reverse

from .base import BackofficeTestCase, bo


class PosDisplayTests(BackofficeTestCase):
    def test_display_is_for_counter_staff(self):
        for role, allowed in ((None, False), ('customer', False), ('expert', False),
                              ('front', True), ('manager', True), ('admin', True)):
            self.login(role)
            with self.subTest(role=role):
                res = self.client.get('/pos-display/')
                self.assertEqual(res.status_code == 200, allowed)

    def test_display_listens_on_the_old_channel_and_has_no_external_assets(self):
        self.login('front')
        page = self.client.get(reverse('pos_display')).content.decode()
        self.assertIn("BroadcastChannel('trustlab_checkout_v2')", page)
        self.assertIn('ยินดีต้อนรับ', page)
        self.assertNotIn('https://', page)

    def test_walkin_page_has_screen_button_and_sends_on_same_channel(self):
        self.login('front')
        page = self.client.get(bo('walkin')).content.decode()
        self.assertIn('id="posBtn"', page)
        self.assertIn("BroadcastChannel('trustlab_checkout_v2')", page)
        self.assertIn(reverse('pos_display'), page)

    @override_settings(PROMPTPAY_RECEIVER_ID='0812345678')
    def test_counter_flow_qr_then_payment(self):
        booking, _ = self.walkin()
        self.login('front')
        qr = self.ok(self.post(bo('booking_qr', booking.pk)))['data']
        self.assertTrue(qr['qr_image'].startswith('data:image/png;base64,'))
        self.assertEqual(qr['amount'], booking.total)
        self.ok(self.post(bo('booking_payment', booking.pk),
                          {'method': 'promptpay', 'reference': 'PP-1', 'amount': booking.total}))
        booking.refresh_from_db()
        self.assertEqual(booking.payment_status, 'paid')
        # Paid: no more QR, and a receipt can be issued straight away.
        self.assertEqual(self.post(bo('booking_qr', booking.pk)).status_code, 400)
        self.ok(self.post(bo('document_issue', booking.pk), {'doc_type': 'receipt'}), 201)

    def test_counter_payment_rejects_wrong_amount(self):
        booking, _ = self.walkin()
        self.login('front')
        res = self.post(bo('booking_payment', booking.pk), {'method': 'cash', 'reference': 'x', 'amount': '1.00'})
        self.assertEqual(res.status_code, 400)

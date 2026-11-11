"""Booking page actions: check-in, counter payment, QR, slip review, cancel, walk-in edit, photos."""
from decimal import Decimal
from unittest import mock

from django.core import mail

from apps.audit.models import WorkflowEvent
from apps.bookings.models import Booking, BookingPhoto, CancellationRequest
from apps.customers.models import Customer
from apps.inspections.models import Job

from .base import BackofficeTestCase, bo, png_data_url


class CheckInTests(BackofficeTestCase):
    def test_check_in_creates_job_with_queue_and_is_repeatable(self):
        booking = self.online_booking()
        self.login('front')
        data = self.ok(self.post(bo('booking_check_in', booking.pk), {'serial_number': 'SN-1', 'color': 'Black'}))
        job = Job.objects.get(booking=booking)
        self.assertEqual(data['data']['queue_no'], job.queue_no)
        self.assertEqual(job.serial_number, 'SN-1')
        self.assertEqual(job.price, Decimal('3000.00'))
        self.assertEqual(job.payment_status, 'unpaid')
        # Second call updates details only (no second job, same queue number).
        self.ok(self.post(bo('booking_check_in', booking.display_id), {'color': 'Beige'}))
        self.assertEqual(Job.objects.filter(booking=booking).count(), 1)
        job.refresh_from_db()
        self.assertEqual(job.color, 'Beige')
        self.assertTrue(WorkflowEvent.objects.filter(action='check_in', booking=booking).exists())

    def test_queue_number_runs_per_day(self):
        _, first = self.walkin()
        _, second = self.walkin(phone='0899999991')
        self.assertTrue(first.queue_no.endswith('-001'))
        self.assertTrue(second.queue_no.endswith('-002'))

    def test_check_in_cancelled_booking_is_refused(self):
        booking = self.online_booking()
        self.login('front')
        self.ok(self.post(bo('booking_cancel', booking.pk), {'reason': 'x'}))
        self.assertEqual(self.post(bo('booking_check_in', booking.pk)).status_code, 400)

    def test_unknown_booking_is_404(self):
        self.login('front')
        self.assertEqual(self.get_json(bo('booking_get', '99999')).status_code, 404)
        self.assertEqual(self.get_json(bo('booking_get', 'abc')).status_code, 400)

    def test_booking_get_includes_photos_and_slip(self):
        booking = self.online_booking(payment_method='transfer', slip=png_data_url())
        self.login('front')
        data = self.ok(self.get_json(bo('booking_get', booking.display_id)))['data']
        self.assertTrue(data['slip_url'])
        self.assertTrue(data['has_slip'])
        self.assertEqual(data['photos'], {'customer': [], 'staff': []})

    def test_booking_rows_filters(self):
        paid, _ = self.walkin(mark_paid=True, reference='R1')
        unpaid = self.online_booking(phone='0855555555', customer_name='Nida Search', brand='Hermes')
        self.login('front')
        rows = self.ok(self.get_json(bo('booking_rows')))['data']
        self.assertEqual({r['id'] for r in rows}, {paid.pk, unpaid.pk})
        rows = self.ok(self.get_json(bo('booking_rows') + '?payment=paid'))['data']
        self.assertEqual([r['id'] for r in rows], [paid.pk])
        rows = self.ok(self.get_json(bo('booking_rows') + '?q=nida'))['data']
        self.assertEqual([r['id'] for r in rows], [unpaid.pk])
        rows = self.ok(self.get_json(bo('booking_rows') + f'?q={unpaid.display_id}'))['data']
        self.assertEqual([r['id'] for r in rows], [unpaid.pk])


class CounterPaymentTests(BackofficeTestCase):
    def test_counter_payment_marks_paid_and_emails(self):
        booking = self.online_booking()
        self.login('front')
        mail.outbox.clear()
        url = bo('booking_payment', booking.pk)
        self.assertEqual(self.post(url, {'method': 'cash', 'reference': 'R', 'amount': '10'}).status_code, 400)
        self.assertEqual(self.post(url, {'method': 'bitcoin', 'reference': 'R', 'amount': '3000'}).status_code, 400)
        self.assertEqual(self.post(url, {'method': 'cash', 'reference': '', 'amount': '3000'}).status_code, 400)
        data = self.ok(self.post(url, {'method': 'credit_card', 'reference': 'EDC-1', 'amount': '3000.00'}))
        self.assertEqual(data['data']['status'], 'paid')
        booking.refresh_from_db()
        self.assertEqual((booking.payment_status, booking.payment_method, booking.status),
                         ('paid', 'credit_card', 'confirmed'))
        self.assertEqual(len(mail.outbox), 1)
        # Paying again is a no-op (no second e-mail, no second event).
        self.ok(self.post(url, {'method': 'cash', 'reference': 'R2', 'amount': '3000'}))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(WorkflowEvent.objects.filter(action='counter_payment', booking=booking).count(), 1)

    def test_counter_payment_updates_existing_job(self):
        booking, job = self.walkin()
        self.ok(self.post(bo('booking_payment', booking.pk), {'method': 'promptpay', 'reference': 'P', 'amount': booking.total}))
        job.refresh_from_db()
        self.assertEqual((job.payment_status, job.payment_method), ('paid', 'promptpay'))

    def test_front_cannot_counter_pay_a_slip_waiting_for_review(self):
        booking = self.online_booking(payment_method='transfer', slip=png_data_url())
        self.login('front')
        res = self.post(bo('booking_payment', booking.pk), {'method': 'cash', 'reference': 'R', 'amount': booking.total})
        self.assertEqual(res.status_code, 403)
        self.login('admin')
        self.ok(self.post(bo('booking_payment', booking.pk), {'method': 'cash', 'reference': 'R', 'amount': booking.total}))

    def test_qr_for_unpaid_booking_only(self):
        booking = self.online_booking()
        self.login('front')
        data = self.ok(self.post(bo('booking_qr', booking.pk)))['data']
        self.assertTrue(data['qr_image'].startswith('data:image/png;base64,'))
        self.assertEqual(data['amount'], '3000.00')
        self.ok(self.post(bo('booking_payment', booking.pk), {'method': 'cash', 'reference': 'R', 'amount': '3000'}))
        self.assertEqual(self.post(bo('booking_qr', booking.pk)).status_code, 400)


class SlipReviewTests(BackofficeTestCase):
    def setUp(self):
        super().setUp()
        self.booking = self.online_booking(payment_method='transfer', slip=png_data_url())
        self.url = bo('booking_slip_review', self.booking.pk)

    def test_admin_approves_slip(self):
        self.login('admin')
        mail.outbox.clear()
        self.assertEqual(self.post(self.url, {'action': 'approve', 'reference': 'T1', 'amount': '1'}).status_code, 400)
        self.assertEqual(self.post(self.url, {'action': 'approve', 'reference': '', 'amount': '3000'}).status_code, 400)
        data = self.ok(self.post(self.url, {'action': 'approve', 'reference': 'T1', 'amount': '3000.00'}))
        self.assertEqual(data['data']['status'], 'paid')
        self.booking.refresh_from_db()
        self.assertEqual((self.booking.payment_status, self.booking.status), ('paid', 'confirmed'))
        self.assertEqual(len(mail.outbox), 1)
        self.assertTrue(WorkflowEvent.objects.filter(action='payment_approve', booking=self.booking).exists())

    def test_admin_rejects_slip_then_front_takes_cash(self):
        self.login('admin')
        self.ok(self.post(self.url, {'action': 'reject', 'reference': 'blurry slip'}))
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.payment_status, 'rejected')
        self.login('front')
        self.ok(self.post(bo('booking_payment', self.booking.pk), {'method': 'cash', 'reference': 'R', 'amount': '3000'}))

    def test_only_admin_may_review(self):
        for role in ('front', 'manager', 'expert'):
            self.login(role)
            self.assertEqual(self.post(self.url, {'action': 'approve', 'reference': 'T', 'amount': '3000'}).status_code,
                             403, role)

    def test_shop_booking_cannot_be_approved_as_slip(self):
        shop = self.online_booking(phone='0866666666')
        self.login('admin')
        res = self.post(bo('booking_slip_review', shop.pk), {'action': 'approve', 'reference': 'T', 'amount': '3000'})
        self.assertEqual(res.status_code, 400)


class CancelTests(BackofficeTestCase):
    def test_unpaid_booking_cancels_at_once(self):
        booking, job = self.walkin()
        data = self.ok(self.post(bo('booking_cancel', booking.pk), {'reason': 'no show'}))['data']
        self.assertEqual(data['status'], 'cancelled')
        booking.refresh_from_db()
        job.refresh_from_db()
        self.assertEqual((booking.status, job.status), ('cancelled', 'cancelled'))
        self.assertEqual(self.post(bo('booking_cancel', booking.pk), {}).status_code, 400)  # already cancelled

    def test_manager_cancels_paid_booking_at_once(self):
        booking, _ = self.walkin(mark_paid=True, reference='R')
        self.login('manager')
        self.assertEqual(self.ok(self.post(bo('booking_cancel', booking.pk), {'reason': 'x'}))['data']['status'],
                         'cancelled')

    def test_paid_cancel_flow_with_refund_reference(self):
        booking, _ = self.walkin(mark_paid=True, reference='R')
        self.ok(self.post(bo('booking_cancel', booking.pk), {'reason': 'changed mind'}))
        cancel = CancellationRequest.objects.get(booking=booking)
        url = bo('cancellation_review', cancel.pk)
        self.assertEqual(self.post(url, {'action': 'refund', 'reference': 'X'}).status_code, 400)  # not approved yet
        self.ok(self.post(url, {'action': 'approve', 'refund_amount': '2500'}))
        self.assertEqual(self.post(url, {'action': 'refund', 'reference': ''}).status_code, 400)
        self.ok(self.post(url, {'action': 'refund', 'reference': 'KBANK-123'}))
        cancel.refresh_from_db()
        self.assertEqual((cancel.status, cancel.refund_status, cancel.refund_amount),
                         ('approved', 'paid_out', Decimal('2500.00')))
        self.login('admin')
        stats = self.ok(self.get_json(bo('report_data')))['data']['stats']
        self.assertEqual(stats['refunds'], 2500.0)
        self.assertEqual(stats['total_revenue'], 500.0)

    def test_reject_keeps_booking(self):
        booking, _ = self.walkin(mark_paid=True, reference='R')
        self.ok(self.post(bo('booking_cancel', booking.pk), {'reason': 'x'}))
        cancel = CancellationRequest.objects.get(booking=booking)
        self.ok(self.post(bo('cancellation_review', cancel.pk), {'action': 'reject'}))
        booking.refresh_from_db()
        self.assertEqual(booking.status, 'confirmed')

    def test_cancel_revokes_certificate(self):
        booking, job = self.walkin(mark_paid=True, reference='R')
        self.complete_job(job, code='TL-CANCEL-1')
        self.login('manager')
        self.ok(self.post(bo('booking_cancel', booking.pk), {'reason': 'error'}))
        self.assertEqual(job.certificate.__class__.objects.get(job=job).cert_status, 'revoked')


class WalkinTests(BackofficeTestCase):
    def test_walkin_retry_with_same_key_returns_same_booking_even_a_minute_later(self):
        self.login('front')
        payload = self.booking_payload(mark_paid=True, reference='R1')
        self.ok(self.post(bo('walkin_create'), payload), 201)
        first = Booking.objects.get()
        later = first.booking_time.replace(minute=(first.booking_time.minute + 1) % 60)
        from django.utils import timezone
        fake_now = timezone.localtime().replace(hour=later.hour, minute=later.minute)
        with mock.patch('apps.inspections.services.walkin_service.timezone.localtime', return_value=fake_now):
            self.ok(self.post(bo('walkin_create'), payload), 201)
        self.assertEqual(Booking.objects.count(), 1)
        self.assertEqual(Job.objects.count(), 1)
        self.assertEqual(WorkflowEvent.objects.filter(action='counter_payment').count(), 1)

    def test_walkin_quote_staff_may_set_manual_price(self):
        self.login('front')
        url = bo('walkin_quote')
        self.assertEqual(self.post(url, self.booking_payload(manual_service_amount='800')).status_code, 400)
        q = self.ok(self.post(url, self.booking_payload(manual_service_amount='800', price_reason='promo')))['data']
        self.assertEqual(q['total'], '800.00')

    def test_customer_lookup(self):
        self.login('front')
        self.assertIsNone(self.ok(self.get_json(bo('walkin_customer') + '?phone=000'))['data'])
        data = self.ok(self.get_json(bo('walkin_customer') + '?phone=081-111-1111'))['data']
        self.assertEqual(data['full_name'], 'Member One')

    def test_update_reprices_unpaid_and_keeps_paid_price(self):
        booking, job = self.walkin()
        self.ok(self.post(bo('walkin_update', booking.pk), {'service_package': 'cert_15d', 'serial_number': 'S9'}))
        booking.refresh_from_db()
        job.refresh_from_db()
        self.assertEqual(booking.total, '1000.00')
        self.assertEqual((job.price, job.serial_number, job.service_package), (Decimal('1000.00'), 'S9', 'cert_15d'))
        self.ok(self.post(bo('booking_payment', booking.pk), {'method': 'cash', 'reference': 'R', 'amount': '1000'}))
        self.ok(self.post(bo('walkin_update', booking.pk), {'service_package': 'cert_90d'}))
        booking.refresh_from_db()
        self.assertEqual(booking.total, '1000.00')  # paid price never changes

    def test_update_phone_of_another_customer_is_a_clear_error(self):
        booking, _ = self.walkin()
        res = self.post(bo('walkin_update', booking.pk), {'customer_phone': '0811111111'})  # the member's phone
        self.assertEqual(res.status_code, 400)
        self.assertIn('เบอร์โทรนี้เป็นของลูกค้ารายอื่น', res.json()['message'])
        self.assertEqual(Customer.objects.get(pk=booking.customer_id).phone_number, '0812345678')

    def test_update_switch_to_shipping_sets_return_status(self):
        booking, job = self.walkin()
        address = {'return_address_name': 'A', 'return_phone': '0812345678', 'return_address_detail': '1 Road',
                   'return_subdistrict': 'S', 'return_district': 'D', 'return_province': 'Bangkok',
                   'return_postal_code': '10110'}
        self.ok(self.post(bo('walkin_update', booking.pk), {'delivery_method': 'shipping', **address}))
        booking.refresh_from_db()
        job.refresh_from_db()
        self.assertEqual(booking.total, '3100.00')
        self.assertEqual(job.shipping_status, 'pending_return')


class PhotoTests(BackofficeTestCase):
    def test_staff_photos_add_and_delete(self):
        booking, job = self.walkin()
        self.login('expert')
        data = self.ok(self.post(bo('booking_photos_add', booking.pk), {'photos': [png_data_url(), png_data_url('blue')]}), 201)
        self.assertEqual(len(data['data']), 2)
        photo_id = data['data'][0]['id']
        self.ok(self.post(bo('booking_photo_delete', booking.pk, photo_id)))
        self.assertEqual(BookingPhoto.objects.filter(booking=booking).count(), 1)
        self.assertEqual(self.post(bo('booking_photo_delete', booking.pk, photo_id)).status_code, 404)
        self.assertEqual(self.post(bo('booking_photos_add', booking.pk), {'photos': []}).status_code, 400)

    def test_photo_zip(self):
        booking, job = self.walkin()
        self.ok(self.post(bo('booking_photos_add', booking.pk), {'photos': [png_data_url()]}), 201)
        status_url = self.ok(self.post(bo('job_photo_zip', job.pk)))['data']['status_url']
        status = self.ok(self.get_json(status_url))['data']
        self.assertEqual(status['status'], 'ready', status)
        self.assertEqual(self.client.get(status['download_url']).status_code, 200)

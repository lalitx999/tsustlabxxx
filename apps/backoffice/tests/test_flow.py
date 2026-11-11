"""Plan item 1.2 — one full business flow, start to finish, through the real endpoints.

online booking + slip -> admin approves slip -> front desk check-in -> expert result ->
certificate -> public verify + PDF -> return shipping -> report totals.
"""
from django.core import mail
from django.urls import reverse

from apps.audit.models import WorkflowEvent
from apps.bookings.models import Booking
from apps.inspections.models import Certificate, Job

from .base import BackofficeTestCase, bo, png_data_url
from .test_certificates import SHIP_ADDRESS


class FullFlowTests(BackofficeTestCase):
    def test_online_booking_to_report(self):
        mail.outbox.clear()

        # 1. Customer books online, pays by transfer, attaches the slip, wants the item shipped back.
        self.client.logout()
        data = self.booking_payload(payment_method='transfer', **SHIP_ADDRESS)
        quote = self.ok(self.post(reverse('website:booking_quote'), data))['data']
        self.assertEqual(quote['total'], '3100.00')  # 3,000 + 100 shipping
        data.update(quote_token=quote['quote_token'], slip=png_data_url())
        created = self.ok(self.post(reverse('website:booking_create'), data), 201)['data']
        booking = Booking.objects.get()
        self.assertEqual((booking.payment_status, booking.status), ('pending_review', 'pending'))
        receipt = self.client.get(created['receipt_url'])
        self.assertContains(receipt, booking.display_id)
        self.assertEqual(len(mail.outbox), 0)  # not paid yet -> no payment e-mail

        # 2. Admin checks the slip on Operations and approves it.
        self.login('admin')
        self.assertContains(self.client.get(bo('operations')), booking.display_id)
        self.ok(self.post(bo('booking_slip_review', booking.pk),
                          {'action': 'approve', 'reference': 'KBANK-0001', 'amount': '3100.00'}))
        booking.refresh_from_db()
        self.assertEqual((booking.payment_status, booking.status), ('paid', 'confirmed'))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('ยืนยันการชำระเงิน', mail.outbox[0].subject)

        # 3. Customer arrives; front desk receives the item and issues a queue number.
        self.login('front')
        check_in = self.ok(self.post(bo('booking_check_in', booking.display_id),
                                     {'serial_number': 'CH-998877', 'color': 'Black', 'accessories': 'dust bag'}))
        job = Job.objects.get(booking=booking)
        self.assertEqual(check_in['data']['queue_no'], job.queue_no)
        self.assertEqual((job.payment_status, job.shipping_status), ('paid', 'pending_return'))
        self.ok(self.post(bo('booking_photos_add', booking.pk), {'photos': [png_data_url(), png_data_url('green')]}), 201)

        # 4. Expert takes the job and records the result -> certificate is issued.
        self.login('expert')
        self.ok(self.post(bo('job_result', job.pk), {'status': 'in_progress', 'expert_id': self.users['expert'].pk}))
        self.ok(self.post(bo('job_result', job.pk), {'status': 'completed', 'result': 'authentic',
                                                     'cert_code': 'TL-FLOW-0001'}))
        cert = Certificate.objects.get(job=job)
        self.assertEqual((cert.cert_code, cert.cert_status, cert.validity_days), ('TL-FLOW-0001', 'authentic', 90))
        self.assertEqual(len(mail.outbox), 2)
        self.assertIn('แจ้งผลการตรวจสอบ', mail.outbox[1].subject)
        booking.refresh_from_db()
        self.assertEqual(booking.status, 'completed')

        # 5. Anyone can verify the certificate and download its PDF; no personal data is shown.
        self.client.logout()
        self.assertEqual(self.client.get(reverse('website:verify') + '?id=TL-FLOW-0001').status_code, 200)
        verify = self.ok(self.get_json(reverse('website:verify_lookup') + '?id=tl-flow-0001'))['data']
        self.assertEqual((verify['status'], verify['serial_number'], verify['brand']), ('authentic', 'CH-998877', 'Chanel'))
        self.assertEqual(len(verify['photos']), 2)
        body = str(verify)
        for private in ('Somchai', '0812345678', 'somchai@example.com', 'Sukhumvit'):
            self.assertNotIn(private, body)
        status_url = self.ok(self.post(verify['pdf_url']))['data']['status_url']
        status = self.ok(self.get_json(status_url))['data']
        self.assertEqual(status['status'], 'ready', status)
        pdf = self.client.get(status['download_url'])
        self.assertTrue(b''.join(pdf.streaming_content).startswith(b'%PDF'))

        # The receipt link now shows the finished result.
        receipt = self.client.get(created['receipt_url'])
        self.assertContains(receipt, booking.display_id)

        # 6. Return shipping: pack, ship with tracking, delivered.
        self.login('front')
        for step, extra in (('ready_to_ship', {}), ('shipped', {'tracking_number': 'TH0001'}), ('delivered', {})):
            self.ok(self.post(bo('job_shipping', job.pk), {'shipping_status': step, **extra}))
        job.refresh_from_db()
        self.assertEqual((job.shipping_status, job.tracking_number), ('delivered', 'TH0001'))

        # 7. Report: one job, authentic, 3,100 received by transfer incl. 100 shipping.
        self.login('manager')
        stats = self.ok(self.get_json(bo('report_data')))['data']['stats']
        self.assertEqual((stats['total_jobs'], stats['completed_jobs'], stats['authentic_jobs']), (1, 1, 1))
        self.assertEqual((stats['revenue_transfer'], stats['shipping_received'], stats['total_revenue']),
                         (3100.0, 100.0, 3100.0))
        self.assertEqual(sum(stats[k] for k in ('revenue_cash', 'revenue_card', 'revenue_promptpay', 'revenue_member')), 0)

        # Audit trail has every staff step.
        actions = list(WorkflowEvent.objects.order_by('pk').values_list('action', flat=True))
        for action in ('payment_approve', 'check_in', 'photos_added', 'inspection', 'shipping'):
            self.assertIn(action, actions)

    def test_member_wallet_booking_and_own_cancel(self):
        from decimal import Decimal

        from apps.customers.services.credit_service import change_credit
        change_credit(self.member, Decimal('5000'), 'seed', 'seed', self.users['admin'])
        self.login('customer')
        data = self.booking_payload(payment_method='wallet', phone='0811111111')
        data['quote_token'] = self.ok(self.post(reverse('website:booking_quote'), data))['data']['quote_token']
        self.ok(self.post(reverse('website:booking_create'), data), 201)
        booking = Booking.objects.get()
        self.assertEqual((booking.customer_id, booking.payment_status), (self.member.pk, 'paid'))
        self.member.refresh_from_db()
        self.assertEqual(self.member.credit_balance, Decimal('2000.00'))
        self.assertContains(self.client.get(reverse('website:member_dashboard')), booking.display_id)
        # Paid booking: member's cancel becomes a request for staff to review.
        res = self.ok(self.post(reverse('website:member_cancel', args=[booking.pk]), {'reason': 'busy'}))
        self.assertEqual(res['data']['status'], 'pending')
        # Report counts wallet payments as member revenue.
        self.login('admin')
        self.assertEqual(self.ok(self.get_json(bo('report_data')))['data']['stats']['revenue_member'], 3000.0)

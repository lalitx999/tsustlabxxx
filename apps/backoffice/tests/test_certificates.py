"""Job result, certificate page actions (PDF, e-mail, change code, revoke, expire), shipping and label."""
from django.core import mail
from django.test import override_settings

from apps.core.models import GeneratedFile
from apps.inspections.models import Certificate, CertificateSendLog, Job

from .base import BackofficeTestCase, bo, png_data_url


class JobResultTests(BackofficeTestCase):
    def test_stage_then_complete_issues_certificate(self):
        _, job = self.walkin(mark_paid=True, reference='R')
        self.login('expert')
        self.ok(self.post(bo('job_result', job.pk), {'status': 'in_progress', 'expert_id': self.users['expert'].pk}))
        job.refresh_from_db()
        self.assertEqual((job.status, job.expert_source), ('in_progress', 'Expert User'))
        self.assertEqual(self.post(bo('job_result', job.pk), {'status': 'completed'}).status_code, 400)  # no result
        self.assertEqual(self.post(bo('job_result', job.pk), {'status': 'done', 'result': 'authentic'}).status_code, 400)
        data = self.complete_job(job, code='TL-JOB-0001')['data']
        self.assertEqual((data['status'], data['certificate_code']), ('completed', 'TL-JOB-0001'))
        job.booking.refresh_from_db()
        self.assertEqual(job.booking.status, 'completed')

    def test_fake_result_gives_unauthentic_certificate(self):
        _, job = self.walkin()
        self.complete_job(job, result='fake')
        cert = Certificate.objects.get(job=job)
        self.assertEqual(cert.cert_status, 'unauthentic')
        self.assertTrue(cert.cert_code.startswith('TL-'))

    def test_inconclusive_and_photo_review_have_no_certificate(self):
        _, job = self.walkin()
        self.complete_job(job, result='inconclusive')
        _, photo_job = self.walkin(phone='0844444444', service_package='photo_review', photos=[png_data_url()])
        self.complete_job(photo_job, result='authentic')
        self.assertFalse(Certificate.objects.exists())

    def test_result_locked_once_certificate_exists(self):
        _, job = self.walkin()
        self.complete_job(job, code='TL-LOCK-1')
        self.login('expert')
        res = self.post(bo('job_result', job.pk), {'status': 'completed', 'result': 'fake'})
        self.assertEqual(res.status_code, 400)

    def test_duplicate_cert_code_rejected(self):
        _, job1 = self.walkin()
        _, job2 = self.walkin(phone='0833333333')
        self.complete_job(job1, code='TL-DUP-1')
        self.login('expert')
        res = self.post(bo('job_result', job2.pk), {'status': 'completed', 'result': 'authentic', 'cert_code': 'TL-DUP-1'})
        self.assertEqual(res.status_code, 400)
        job2.refresh_from_db()
        self.assertEqual(job2.status, 'pending')  # whole save rolled back

    def test_cancelled_job_cannot_get_result(self):
        booking, job = self.walkin()
        self.ok(self.post(bo('booking_cancel', booking.pk), {'reason': 'x'}))
        self.login('expert')
        self.assertEqual(self.post(bo('job_result', job.pk), {'status': 'completed', 'result': 'authentic'}).status_code, 400)

    def test_job_rows_and_detail(self):
        _, job = self.walkin()
        self.login('expert')
        rows = self.ok(self.get_json(bo('job_rows') + '?status=pending,in_progress'))['data']
        self.assertEqual([r['id'] for r in rows], [job.pk])
        self.assertEqual(self.ok(self.get_json(bo('job_rows') + '?status=completed'))['data'], [])
        detail = self.ok(self.get_json(bo('job_get', job.display_id)))['data']
        self.assertEqual(detail['photos'], {'customer': [], 'staff': []})

    def test_front_edits_item_details(self):
        _, job = self.walkin()
        self.ok(self.post(bo('job_details', job.pk), {'serial_number': 'NEW-SN', 'accessories': 'dust bag'}))
        job.refresh_from_db()
        self.assertEqual((job.serial_number, job.accessories), ('NEW-SN', 'dust bag'))


class CertificatePageTests(BackofficeTestCase):
    def setUp(self):
        super().setUp()
        _, self.job = self.walkin(mark_paid=True, reference='R')
        self.complete_job(self.job, code='TL-CERT-0001')
        self.cert = Certificate.objects.get(job=self.job)

    def test_rows_and_search(self):
        self.login('front')
        rows = self.ok(self.get_json(bo('certificate_rows')))['data']
        self.assertEqual(rows[0]['code'], 'TL-CERT-0001')
        self.assertEqual(rows[0]['email'], 'somchai@example.com')
        self.assertEqual(self.ok(self.get_json(bo('certificate_rows') + '?status=revoked'))['data'], [])
        self.assertEqual(len(self.ok(self.get_json(bo('certificate_rows') + '?q=chanel'))['data']), 1)

    def test_pdf_is_built_in_background_and_downloadable(self):
        self.login('front')
        status_url = self.ok(self.post(bo('certificate_pdf', 'TL-CERT-0001')))['data']['status_url']
        status = self.ok(self.get_json(status_url))['data']
        self.assertEqual(status['status'], 'ready', status)
        res = self.client.get(status['download_url'])
        self.assertEqual(res['Content-Type'], 'application/pdf')
        self.assertTrue(b''.join(res.streaming_content).startswith(b'%PDF'))
        # Same certificate state -> same file (no second build).
        self.ok(self.post(bo('certificate_pdf', 'TL-CERT-0001')))
        self.assertEqual(GeneratedFile.objects.filter(kind='certificate_pdf').count(), 1)

    def test_send_by_email_uses_customer_address_or_recipient(self):
        self.login('front')
        mail.outbox.clear()
        self.ok(self.post(bo('certificate_send', 'TL-CERT-0001'), {'method': 'email', 'recipient': ''}))
        self.ok(self.post(bo('certificate_send', 'TL-CERT-0001'), {'method': 'email', 'recipient': 'other@example.com'}))
        self.assertEqual([m.to for m in mail.outbox], [['somchai@example.com'], ['other@example.com']])
        self.assertEqual(CertificateSendLog.objects.filter(certificate=self.cert).count(), 2)
        self.assertEqual(self.post(bo('certificate_send', 'TL-CERT-0001'), {'method': 'fax'}).status_code, 400)
        self.assertEqual(self.post(bo('certificate_send', 'TL-CERT-0001'), {'method': 'line'}).status_code, 400)

    def test_send_by_line_without_token_is_skipped_safely(self):
        self.login('front')
        self.ok(self.post(bo('certificate_send', 'TL-CERT-0001'), {'method': 'line', 'recipient': 'U123'}))
        self.assertTrue(CertificateSendLog.objects.filter(method='line').exists())

    def test_change_code_updates_tag_and_verify(self):
        self.job.tag_code = 'TL-CERT-0001'
        self.job.save(update_fields=['tag_code'])
        self.login('front')
        self.assertEqual(self.post(bo('certificate_code', 'TL-CERT-0001'), {'cert_code': 'bad/code'}).status_code, 400)
        self.assertEqual(self.post(bo('certificate_code', 'TL-CERT-0001'), {'cert_code': ''}).status_code, 400)
        self.ok(self.post(bo('certificate_code', 'TL-CERT-0001'), {'cert_code': 'TL-CERT-0002'}))
        self.job.refresh_from_db()
        self.assertEqual(self.job.tag_code, 'TL-CERT-0002')
        self.client.logout()
        self.assertEqual(self.get_json('/verify/lookup/?id=TL-CERT-0002').status_code, 200)
        self.assertEqual(self.get_json('/verify/lookup/?id=TL-CERT-0001').status_code, 404)

    def test_revoke_and_expire_admin_only(self):
        for role in ('front', 'manager', 'expert'):
            self.login(role)
            self.assertEqual(self.post(bo('certificate_revoke', 'TL-CERT-0001'), {'reason': 'x'}).status_code, 403)
        self.login('admin')
        self.ok(self.post(bo('certificate_revoke', 'TL-CERT-0001'), {'reason': 'wrong item'}))
        self.client.logout()
        data = self.ok(self.get_json('/verify/lookup/?id=TL-CERT-0001'))['data']
        self.assertEqual((data['status'], data['revoke_reason']), ('revoked', 'wrong item'))
        self.login('admin')
        self.ok(self.post(bo('certificate_expire', 'TL-CERT-0001')))
        self.cert.refresh_from_db()
        self.assertEqual(self.cert.cert_status, 'expired')

    def test_select_photos_only_from_this_booking(self):
        self.login('expert')
        photo = self.ok(self.post(bo('booking_photos_add', self.job.booking_id), {'photos': [png_data_url()]}), 201)['data'][0]
        self.ok(self.post(bo('certificate_photos', 'TL-CERT-0001'), {'photo_ids': [photo['id'], 999999]}))
        self.cert.refresh_from_db()
        self.assertEqual(self.cert.selected_photos, [photo['id']])
        self.assertEqual(self.post(bo('certificate_photos', 'TL-CERT-0001'), {'photo_ids': ['x']}).status_code, 400)

    def test_manual_issue_endpoint(self):
        _, job = self.walkin(phone='0822222299')
        self.login('expert')
        self.assertEqual(self.post(bo('certificate_issue'), {'job_id': job.pk}).status_code, 400)  # not completed
        Job.objects.filter(pk=job.pk).update(status='completed', result='authentic')
        self.ok(self.post(bo('certificate_issue'), {'job_id': job.pk, 'cert_code': 'TL-MANUAL-1'}), 201)
        self.assertTrue(Certificate.objects.filter(cert_code='TL-MANUAL-1').exists())


SHIP_ADDRESS = {'delivery_method': 'shipping', 'return_address_name': 'Somchai', 'return_phone': '0812345678',
                'return_address_detail': '99 Sukhumvit', 'return_subdistrict': 'Khlong Toei',
                'return_district': 'Khlong Toei', 'return_province': 'Bangkok', 'return_postal_code': '10110'}


class ShippingTests(BackofficeTestCase):
    def test_shipping_steps_in_order(self):
        _, job = self.walkin(**SHIP_ADDRESS)
        self.assertEqual(job.shipping_status, 'pending_return')
        url = bo('job_shipping', job.pk)
        self.assertEqual(self.post(url, {'shipping_status': 'ready_to_ship'}).status_code, 400)  # not inspected yet
        self.complete_job(job)
        self.login('front')
        self.assertEqual(self.post(url, {'shipping_status': 'shipped'}).status_code, 400)  # skipped a step
        self.ok(self.post(url, {'shipping_status': 'ready_to_ship'}))
        self.assertEqual(self.post(url, {'shipping_status': 'shipped', 'tracking_number': ''}).status_code, 400)
        self.ok(self.post(url, {'shipping_status': 'shipped', 'tracking_number': 'TH123'}))
        self.ok(self.post(url, {'shipping_status': 'delivered'}))
        job.refresh_from_db()
        self.assertEqual((job.shipping_status, job.tracking_number), ('delivered', 'TH123'))

    def test_self_pickup_goes_straight_to_delivered(self):
        _, job = self.walkin()
        self.complete_job(job)
        self.login('front')
        self.ok(self.post(bo('job_shipping', job.pk), {'shipping_status': 'delivered'}))

    def test_label_needs_thai_font(self):
        _, job = self.walkin(**SHIP_ADDRESS)
        self.complete_job(job)
        self.login('front')
        res = self.post(bo('job_label', job.pk))
        self.assertEqual(res.status_code, 400)
        self.assertIn('THAI_FONT_PATH', res.json()['message'])

    @override_settings(THAI_FONT_PATH='/System/Library/Fonts/Supplemental/Tahoma.ttf')
    def test_label_pdf_when_font_is_set(self):
        import os
        if not os.path.exists('/System/Library/Fonts/Supplemental/Tahoma.ttf'):
            self.skipTest('no TTF font on this machine')
        _, job = self.walkin(**SHIP_ADDRESS)
        self.complete_job(job)
        self.login('front')
        status = self.ok(self.get_json(self.ok(self.post(bo('job_label', job.pk)))['data']['status_url']))['data']
        self.assertEqual(status['status'], 'ready', status)

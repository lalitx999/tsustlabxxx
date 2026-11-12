"""Certificate detail page (phase 2.4): info, photo selection, send history, role-based controls."""
from apps.audit.models import WorkflowEvent
from apps.inspections.models import Certificate
from apps.inspections.selectors import job_selector

from .base import BackofficeTestCase, bo, png_data_url

CODE = 'TL-CERT-0001'


class CertificateDetailTests(BackofficeTestCase):
    def setUp(self):
        super().setUp()
        self.booking, self.job = self.walkin(mark_paid=True, reference='R', serial_number='SN-77')
        self.complete_job(self.job, code=CODE)
        self.cert = Certificate.objects.get(job=self.job)

    def add_photos(self, count=1, role='expert'):
        self.login(role)
        res = self.post(bo('booking_photos_add', self.booking.pk), {'photos': [png_data_url()] * count})
        return [p['id'] for p in self.ok(res, 201)['data']]

    def test_page_shows_certificate_product_and_history(self):
        self.login('front')
        self.ok(self.post(bo('certificate_send', CODE), {'method': 'email', 'recipient': 'buyer@example.com'}))
        page = self.client.get(bo('certificate_detail', CODE))
        self.assertEqual(page.status_code, 200)
        for text in (CODE, 'Chanel', 'Classic Flap', self.job.display_id, 'ประวัติการส่งใบเซอร์', 'buyer@example.com',
                     'AUTHENTIC', 'ออกใบเซอร์แล้ว', '/verify'):
            with self.subTest(text=text):
                self.assertContains(page, text)

    def test_unknown_code_is_404_and_lookup_accepts_numeric_id(self):
        self.login('front')
        self.assertEqual(self.client.get(bo('certificate_detail', 'NOPE-404')).status_code, 404)
        self.assertEqual(self.client.get(bo('certificate_detail', str(self.cert.pk))).status_code, 200)

    def test_page_needs_staff(self):
        for role in (None, 'customer'):
            self.login(role)
            self.assertNotEqual(self.client.get(bo('certificate_detail', CODE)).status_code, 200)
        for role in ('front', 'expert', 'manager', 'admin'):
            self.login(role)
            self.assertEqual(self.client.get(bo('certificate_detail', CODE)).status_code, 200)

    def test_admin_only_controls_are_hidden_for_others(self):
        self.login('front')
        page = self.client.get(bo('certificate_detail', CODE)).content.decode()
        self.assertNotIn('data-act="revoke"', page)
        self.assertNotIn('id="savePhotos"', page)  # front desk cannot choose certificate photos
        self.login('admin')
        page = self.client.get(bo('certificate_detail', CODE)).content.decode()
        self.assertIn('data-act="revoke"', page)
        self.assertIn('data-act="expire"', page)

    def test_revoked_certificate_shows_reason(self):
        self.login('admin')
        self.ok(self.post(bo('certificate_revoke', CODE), {'reason': 'wrong item'}))
        page = self.client.get(bo('certificate_detail', CODE))
        self.assertContains(page, 'ถูกระงับ (Revoked)')
        self.assertContains(page, 'wrong item')
        self.assertNotContains(page, 'data-act="revoke"')

    def test_photo_defaults_to_first_three_staff_photos(self):
        ids = self.add_photos(4)
        cert = job_selector.certificate_detail(CODE)
        orders = {p['id']: p['order'] for p in job_selector.certificate_photos(cert)}
        self.assertEqual([orders[i] for i in ids], [1, 2, 3, 0])

    def test_select_photos_keeps_order_and_limits_to_three(self):
        ids = self.add_photos(4)
        self.ok(self.post(bo('certificate_photos', CODE), {'photo_ids': [ids[2], ids[0]]}))
        self.cert.refresh_from_db()
        self.assertEqual(self.cert.selected_photos, [ids[2], ids[0]])
        cert = job_selector.certificate_detail(CODE)
        orders = {p['id']: p['order'] for p in job_selector.certificate_photos(cert)}
        self.assertEqual((orders[ids[2]], orders[ids[0]], orders[ids[1]]), (1, 2, 0))
        self.assertTrue(WorkflowEvent.objects.filter(action='certificate_photos_selected', job=self.job).exists())
        res = self.post(bo('certificate_photos', CODE), {'photo_ids': ids})
        self.assertEqual(res.status_code, 400)
        self.assertIn('สูงสุด 3', res.json()['message'])
        self.assertEqual(self.post(bo('certificate_photos', CODE), {'photo_ids': []}).status_code, 400)
        # Duplicates count once.
        self.ok(self.post(bo('certificate_photos', CODE), {'photo_ids': [ids[1], ids[1]]}))
        self.cert.refresh_from_db()
        self.assertEqual(self.cert.selected_photos, [ids[1]])

    def test_front_desk_cannot_choose_photos(self):
        ids = self.add_photos(1)
        self.login('front')
        self.assertEqual(self.post(bo('certificate_photos', CODE), {'photo_ids': ids}).status_code, 403)

    def test_detail_query_count_does_not_grow_with_photos_and_logs(self):
        def count_queries():
            from django.db import connection
            from django.test.utils import CaptureQueriesContext
            with CaptureQueriesContext(connection) as ctx:
                cert = job_selector.certificate_detail(CODE)
                job_selector.certificate_photos(cert)
                list(cert.send_logs.all())
                _ = (cert.job.customer.full_name, cert.job.booking.branch.name,
                     cert.job.result_recorded_by and cert.job.result_recorded_by.display_name)
            return len(ctx.captured_queries)

        self.add_photos(1)
        before = count_queries()
        self.add_photos(3)
        self.login('front')
        for _ in range(3):
            self.ok(self.post(bo('certificate_send', CODE), {'method': 'email', 'recipient': 'x@example.com'}))
        self.assertEqual(count_queries(), before)

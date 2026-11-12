"""Expert workbench at /authenzs/expert/jobs/ (phase 2.3)."""
from django.urls import reverse

from apps.inspections.models import Certificate, Job

from .base import PASSWORD, BackofficeTestCase, bo, png_data_url


class ExpertWorkbenchTests(BackofficeTestCase):
    def test_page_and_rows_are_for_inspectors_only(self):
        for role, allowed in ((None, False), ('customer', False), ('front', False),
                              ('expert', True), ('manager', True), ('admin', True)):
            self.login(role)
            with self.subTest(role=role):
                page = self.client.get(reverse('expert:jobs'))
                rows = self.get_json(reverse('expert:rows'))
                if allowed:
                    self.assertEqual(page.status_code, 200)
                    self.assertEqual(rows.status_code, 200)
                else:
                    self.assertNotEqual(page.status_code, 200)
                    self.assertIn(rows.status_code, (401, 403))

    def test_rows_include_photos_and_skip_cancelled_jobs(self):
        booking, job = self.walkin()
        _, cancelled = self.walkin(phone='0899999993')
        Job.objects.filter(pk=cancelled.pk).update(status='cancelled')
        self.login('expert')
        self.ok(self.post(bo('booking_photos_add', booking.pk), {'photos': [png_data_url(), png_data_url('blue')]}), 201)
        rows = self.ok(self.get_json(reverse('expert:rows')))['data']
        self.assertEqual([r['id'] for r in rows], [job.pk])
        self.assertEqual(len(rows[0]['photos']), 2)
        self.assertEqual(rows[0]['photos'][0]['type'], 'staff')
        self.assertTrue(rows[0]['photos'][0]['url'])

    def test_rows_query_count_is_flat(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        booking, _ = self.walkin()
        self.login('expert')
        self.ok(self.post(bo('booking_photos_add', booking.pk), {'photos': [png_data_url()]}), 201)
        with CaptureQueriesContext(connection) as one:
            self.ok(self.get_json(reverse('expert:rows')))
        for i in range(3):
            b, _ = self.walkin(phone=f'08999990{i}0')
            self.login('expert')
            self.ok(self.post(bo('booking_photos_add', b.pk), {'photos': [png_data_url()]}), 201)
        with CaptureQueriesContext(connection) as many:
            self.assertEqual(len(self.ok(self.get_json(reverse('expert:rows')))['data']), 4)
        self.assertEqual(len(many.captured_queries), len(one.captured_queries))

    def test_expert_records_result_from_workbench_flow(self):
        _, job = self.walkin(mark_paid=True, reference='R')
        self.login('expert')
        self.ok(self.post(bo('job_result', job.pk), {'status': 'in_progress', 'result': 'pending',
                                                      'expert_instruction': 'ตรวจฝีเข็มแล้ว', 'tag_code': 'TAG-1'}))
        job.refresh_from_db()
        self.assertEqual((job.status, job.result, job.tag_code), ('in_progress', None, 'TAG-1'))
        self.assertEqual(job.result_recorded_by, self.users['expert'])
        self.ok(self.post(bo('job_result', job.pk), {'status': 'completed', 'result': 'authentic'}))
        self.assertTrue(Certificate.objects.filter(job=job).exists())
        row = self.ok(self.get_json(reverse('expert:rows')))['data'][0]
        self.assertTrue(row['certificate_code'])
        # With a certificate, notes can still change but the result cannot.
        self.ok(self.post(bo('job_result', job.pk), {'expert_instruction': 'เพิ่มบันทึก'}))
        self.assertEqual(self.post(bo('job_result', job.pk), {'status': 'completed', 'result': 'fake'}).status_code, 400)

    def test_inconclusive_closes_job_without_certificate(self):
        _, job = self.walkin(mark_paid=True, reference='R')
        self.login('expert')
        self.ok(self.post(bo('job_result', job.pk), {'status': 'completed', 'result': 'inconclusive'}))
        self.assertFalse(Certificate.objects.filter(job=job).exists())

    def test_expert_lands_on_workbench_after_login(self):
        self.client.logout()
        res = self.client.post(reverse('accounts:staff_login'), {'username': 'expert1', 'password': PASSWORD})
        self.assertEqual(res['Location'], reverse('expert:jobs'))
        self.client.logout()
        res = self.client.post(reverse('accounts:staff_login'), {'username': 'front1', 'password': PASSWORD})
        self.assertEqual(res['Location'], reverse('backoffice:dashboard'))
        # An explicit next= still wins.
        self.client.logout()
        res = self.client.post(reverse('accounts:staff_login') + '?next=' + bo('jobs'),
                               {'username': 'expert1', 'password': PASSWORD})
        self.assertEqual(res['Location'], bo('jobs'))

    def test_back_office_link_only_for_admin_and_manager(self):
        self.login('expert')
        self.assertNotContains(self.client.get(reverse('expert:jobs')), 'ระบบหลังบ้าน')
        self.login('manager')
        self.assertContains(self.client.get(reverse('expert:jobs')), 'ระบบหลังบ้าน')

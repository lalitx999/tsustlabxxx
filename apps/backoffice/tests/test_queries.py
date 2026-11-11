"""N+1 guards: list endpoints and list pages must use the same number of queries for 1 row or many.

Each test measures the query count with one row, adds more rows of the same shape, and then
asserts the count with assertNumQueries. A per-row query would make the second count larger.
"""
from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.bookings.models import CancellationRequest
from apps.customers.models import CreditEntry, TopupRequest
from apps.customers.services.credit_service import change_credit

from .base import BackofficeTestCase, bo, png_data_url

PHONES = iter(f'08{n:08d}' for n in range(10000000, 10001000))


class QueryCountTests(BackofficeTestCase):
    def add_rows(self, count):
        """Bookings with a job, photo, certificate, cancellation request, credit entry and top-up."""
        for _ in range(count):
            phone = next(PHONES)
            booking, job = self.walkin(phone=phone, mark_paid=True, reference='R')
            self.post(bo('booking_photos_add', booking.pk), {'photos': [png_data_url()]})
            self.complete_job(job, role='expert')
            CancellationRequest.objects.create(booking=booking, reason='x', status='pending')
            customer = booking.customer
            change_credit(customer, 100, f'seed:{phone}', 'seed', self.users['admin'])
            TopupRequest.objects.create(customer=customer, amount=100)
        self.login('admin')

    def assert_constant(self, fetch, more=3):
        self.add_rows(1)
        connection.queries_log.clear()  # the log is a bounded deque; a full one would count 0
        with CaptureQueriesContext(connection) as first:
            response = fetch()
        expected = len(first.captured_queries)  # read now: the list is a lazy slice of the log
        self.assertEqual(response.status_code, 200)
        self.add_rows(more)
        connection.queries_log.clear()
        with self.assertNumQueries(expected):
            response = fetch()
        self.assertEqual(response.status_code, 200)
        return response

    # ---------------------------------------------------------------- Ajax lists
    def test_booking_rows(self):
        res = self.assert_constant(lambda: self.get_json(bo('booking_rows')))
        self.assertEqual(len(res.json()['data']), 4)

    def test_job_rows(self):
        res = self.assert_constant(lambda: self.get_json(bo('job_rows')))
        self.assertEqual(len(res.json()['data']), 4)

    def test_certificate_rows(self):
        res = self.assert_constant(lambda: self.get_json(bo('certificate_rows')))
        self.assertEqual(len(res.json()['data']), 4)

    def test_customer_rows(self):
        res = self.assert_constant(lambda: self.get_json(bo('customer_rows')))
        self.assertGreaterEqual(len(res.json()['data']), 4)

    # ---------------------------------------------------------------- list pages
    def test_dashboard_page(self):
        self.assert_constant(lambda: self.client.get(bo('dashboard')))

    def test_operations_page(self):
        self.assert_constant(lambda: self.client.get(bo('operations')))

    def test_completed_page(self):
        self.assert_constant(lambda: self.client.get(bo('completed')))

    def test_progress_and_queue_pages(self):
        self.assert_constant(lambda: self.client.get(bo('queue')))
        self.assert_constant(lambda: self.client.get(bo('progress') + '?stage=pending'))

    def test_membership_page(self):
        res = self.assert_constant(lambda: self.client.get(bo('membership')))
        self.assertGreaterEqual(CreditEntry.objects.count(), 4)
        self.assertContains(res, 'คำขอเติมเครดิตรอตรวจสอบ')

    def test_users_and_certificates_pages(self):
        self.assert_constant(lambda: self.client.get(bo('users')))
        self.assert_constant(lambda: self.client.get(bo('certificates')))

    def test_public_verify_lookup(self):
        """Public verify with photos: fixed number of queries."""
        self.add_rows(1)
        from apps.inspections.models import Certificate
        code = Certificate.objects.first().cert_code
        self.client.logout()
        connection.queries_log.clear()
        with self.assertNumQueries(2):  # certificate+job+booking+branch in one join, then booking photos
            self.assertEqual(self.get_json('/verify/lookup/?id=' + code).status_code, 200)

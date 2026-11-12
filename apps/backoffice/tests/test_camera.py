"""TrustLab Cam at /trustlabcam/ (phase 2.1)."""
from django.urls import reverse
from django.utils import timezone

from apps.bookings.models import Booking, BookingPhoto

from .base import PASSWORD, BackofficeTestCase, bo, png_data_url


class TrustLabCamTests(BackofficeTestCase):
    def test_home_shows_cam_login_or_redirects_staff(self):
        self.client.logout()
        page = self.client.get(reverse('camera:home'))
        self.assertContains(page, 'TrustLab')
        self.assertContains(page, 'ระบบกล้องตรวจสอบหน้าร้าน')
        self.login('front')
        self.assertRedirects(self.client.get(reverse('camera:home')), reverse('camera:jobs'))

    def test_cam_login_goes_to_day_list_and_wrong_password_stays_on_cam_screen(self):
        self.client.logout()
        res = self.client.post(reverse('accounts:staff_login'),
                               {'username': 'front1', 'password': 'wrong', 'next': '/trustlabcam/jobs/'})
        self.assertContains(res, 'ระบบกล้องตรวจสอบหน้าร้าน')  # Cam-style screen, not the dark back-office one
        self.assertContains(res, 'ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง')
        res = self.client.post(reverse('accounts:staff_login'),
                               {'username': 'front1', 'password': PASSWORD, 'next': '/trustlabcam/jobs/'})
        self.assertEqual(res['Location'], '/trustlabcam/jobs/')

    def test_pages_need_staff(self):
        booking, _ = self.walkin()
        urls = [reverse('camera:jobs'), reverse('camera:capture', args=[booking.pk])]
        for role in (None, 'customer'):
            self.login(role)
            for url in urls:
                self.assertNotEqual(self.client.get(url).status_code, 200)
            self.assertIn(self.get_json(reverse('camera:rows')).status_code, (401, 403))
        for role in ('front', 'expert', 'manager', 'admin'):
            self.login(role)
            for url in urls:
                self.assertEqual(self.client.get(url).status_code, 200, (role, url))

    def test_day_list_counts_staff_photos_only(self):
        booking, job = self.walkin()
        BookingPhoto.objects.create(booking=booking, photo_type='customer', photo='booking_photos/x.png')
        self.login('front')
        self.ok(self.post(bo('booking_photos_add', booking.pk), {'photos': [png_data_url(), png_data_url('blue')]}), 201)
        rows = self.ok(self.get_json(reverse('camera:rows')))['data']
        row = next(r for r in rows if r['id'] == booking.pk)
        self.assertEqual(row['staff_photos'], 2)
        self.assertEqual(row['queue_no'], job.queue_no)

    def test_day_list_filters_by_date(self):
        booking, _ = self.walkin()
        Booking.objects.filter(pk=booking.pk).update(booking_date='2099-01-02')
        Booking.objects.filter(pk=booking.pk).update(created_at=timezone.now().replace(year=2098))
        self.login('front')
        self.assertEqual(self.ok(self.get_json(reverse('camera:rows') + '?date=2099-01-02'))['data'][0]['id'], booking.pk)
        today = self.ok(self.get_json(reverse('camera:rows')))['data']
        self.assertNotIn(booking.pk, [r['id'] for r in today])
        self.assertEqual(self.get_json(reverse('camera:rows') + '?date=not-a-date').status_code, 400)

    def test_day_list_query_count_is_flat(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        self.walkin()
        self.login('front')
        with CaptureQueriesContext(connection) as one:
            self.ok(self.get_json(reverse('camera:rows')))
        for i in range(3):
            self.walkin(phone=f'08999991{i}0')
        self.login('front')
        with CaptureQueriesContext(connection) as many:
            self.assertEqual(len(self.ok(self.get_json(reverse('camera:rows')))['data']), 4)
        self.assertEqual(len(many.captured_queries), len(one.captured_queries))

    def test_capture_page_shows_booking_and_upload_limit(self):
        booking, _ = self.walkin()
        self.login('front')
        page = self.client.get(reverse('camera:capture', args=[booking.pk]))
        self.assertContains(page, booking.display_id)
        self.assertContains(page, 'Chanel')
        self.assertContains(page, bo('booking_photos_add', booking.pk))
        self.assertEqual(self.client.get(reverse('camera:capture', args=[999999])).status_code, 404)
        # The upload endpoint the camera uses still enforces 30 staff photos.
        self.ok(self.post(bo('booking_photos_add', booking.pk), {'photos': [png_data_url()] * 30}), 201)
        self.assertEqual(self.post(bo('booking_photos_add', booking.pk), {'photos': [png_data_url()]}).status_code, 400)

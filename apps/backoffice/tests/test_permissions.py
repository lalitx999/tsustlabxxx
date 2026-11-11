"""Role matrix: every back-office page and Ajax endpoint for anonymous, customer and each staff role.

Allowed roles must never get 401/403 (they may get 400/404 because the test sends empty data
and ids that do not exist, so nothing is changed). Everyone else must be refused.
"""
from django.urls import reverse

from .base import BackofficeTestCase, bo

ST = ('admin', 'manager', 'front', 'expert')
FD = ('admin', 'manager', 'front')
AD = ('admin',)
INS = ('admin', 'manager', 'expert')
ROLES = (None, 'customer') + ST

PAGES = {
    'dashboard': ST, 'walkin': FD, 'bookings': FD, 'jobs': ST, 'queue': ST, 'operations': FD, 'progress': ST,
    'completed': ST, 'certificates': ST, 'qr': ST, 'customers': ST, 'membership': ST, 'inquiries': ST,
    'reports': ST, 'analytics': ST, 'users': AD, 'pricing': AD, 'promos': AD, 'system': AD,
}

GET_ENDPOINTS = [
    (bo('walkin_customer') + '?phone=0800000000', FD),
    (bo('booking_rows'), FD),
    (bo('booking_get', '99999'), FD),
    (bo('job_rows'), ST),
    (bo('job_get', '99999'), ST),
    (bo('certificate_rows'), ST),
    (bo('customer_rows'), ST),
    (bo('report_data'), ST),
]

POST_ENDPOINTS = [
    (bo('walkin_quote'), FD), (bo('walkin_create'), FD), (bo('walkin_update', 99999), FD),
    (bo('booking_check_in', '99999'), FD), (bo('booking_payment', '99999'), FD), (bo('booking_qr', '99999'), FD),
    (bo('booking_slip_review', '99999'), AD), (bo('booking_cancel', '99999'), FD),
    (bo('booking_photos_add', '99999'), ST), (bo('booking_photo_delete', '99999', 1), ST),
    (bo('cancellation_review', 99999), FD),
    (bo('job_result', '99999'), INS), (bo('job_details', '99999'), FD), (bo('job_shipping', '99999'), FD),
    (bo('job_label', '99999'), FD), (bo('job_photo_zip', '99999'), ST),
    (bo('certificate_issue'), INS), (bo('certificate_code', 'NOPE'), ST), (bo('certificate_revoke', 'NOPE'), AD),
    (bo('certificate_expire', 'NOPE'), AD), (bo('certificate_send', 'NOPE'), ST),
    (bo('certificate_photos', 'NOPE'), INS), (bo('certificate_pdf', 'NOPE'), ST),
    (bo('customer_credit'), AD), (bo('topup_review', 99999), AD), (bo('inquiry_update', 'contact', 99999), ST),
    (bo('report_pdf'), ST),
    (bo('user_create'), AD), (bo('user_save', 99999), AD), (bo('pricing_save'), AD),
    (bo('promo_create'), AD), (bo('promo_save', 99999), AD),
]


class RoleMatrixTests(BackofficeTestCase):
    def denied_status(self, role):
        return 401 if role is None else 403

    def test_pages(self):
        for name, allowed in PAGES.items():
            for role in ROLES:
                self.login(role)
                res = self.client.get(bo(name))
                if role in allowed:
                    self.assertEqual(res.status_code, 200, f'{name} as {role}')
                else:
                    self.assertEqual(res.status_code, 302, f'{name} as {role}')
                    self.assertIn(reverse('accounts:staff_login'), res['Location'])

    def test_ajax_get(self):
        for url, allowed in GET_ENDPOINTS:
            for role in ROLES:
                self.login(role)
                status = self.get_json(url).status_code
                if role in allowed:
                    self.assertNotIn(status, (401, 403), f'{url} as {role}')
                else:
                    self.assertEqual(status, self.denied_status(role), f'{url} as {role}')

    def test_ajax_post(self):
        for url, allowed in POST_ENDPOINTS:
            for role in ROLES:
                self.login(role)
                status = self.post(url, {}).status_code
                if role in allowed:
                    self.assertNotIn(status, (401, 403), f'{url} as {role}')
                else:
                    self.assertEqual(status, self.denied_status(role), f'{url} as {role}')

    def test_wrong_method_is_rejected(self):
        self.login('admin')
        self.assertEqual(self.get_json(bo('walkin_create')).status_code, 405)
        self.assertEqual(self.post(bo('booking_rows')).status_code, 405)

    def test_inactive_staff_is_logged_out_of_backoffice(self):
        user = self.users['admin']
        user.is_active = False
        user.save()
        self.client.force_login(user)
        self.assertEqual(self.client.get(bo('dashboard')).status_code, 302)


class MenuTests(BackofficeTestCase):
    """Sidebar shows only what each role may open."""
    EXPECT = {
        'front': {'Walk-in (New Sale)': True, 'Booking': True, 'Operations &amp; Delivery': True, 'Users': False,
                  'Services &amp; Pricing': False, 'Promo Codes': False, 'System Settings': False},
        'manager': {'Walk-in (New Sale)': True, 'Booking': True, 'Users': False, 'Promo Codes': False},
        'expert': {'Job List': True, 'Walk-in (New Sale)': False, 'Booking': False,
                   'Operations &amp; Delivery': False, 'Users': False},
        'admin': {'Walk-in (New Sale)': True, 'Users': True, 'Services &amp; Pricing': True, 'Promo Codes': True,
                  'System Settings': True},
    }

    def test_menu_per_role(self):
        for role, items in self.EXPECT.items():
            self.login(role)
            html = self.client.get(bo('dashboard')).content.decode()
            nav = html[html.index('<nav class="bo-nav">'):html.index('</nav>')]
            for label, visible in items.items():
                self.assertEqual(f'<span>{label}</span>' in nav, visible, f'{label} for {role}')


class PublicAccessTests(BackofficeTestCase):
    def test_member_pages_need_customer_login(self):
        for name in ('member_dashboard', 'member_profile'):
            self.client.logout()
            self.assertEqual(self.client.get(reverse(f'website:{name}')).status_code, 302)
            self.login('front')  # staff are not members
            self.assertEqual(self.client.get(reverse(f'website:{name}')).status_code, 302)
            self.login('customer')
            self.assertEqual(self.client.get(reverse(f'website:{name}')).status_code, 200)

    def test_member_ajax_refuses_others(self):
        self.client.logout()
        self.assertEqual(self.post(reverse('website:member_topup'), {'amount': '500'}).status_code, 401)
        self.login('front')
        self.assertEqual(self.post(reverse('website:member_topup'), {'amount': '500'}).status_code, 403)

    def test_expert_cannot_create_booking_but_anonymous_can(self):
        self.login('expert')
        self.assertEqual(self.post(reverse('website:booking_create'), self.booking_payload()).status_code, 403)
        self.online_booking()

    def test_qr_sticker_is_staff_only(self):
        url = reverse('website:qr_image') + '?text=https://example.com/verify/?id=TL-1'
        self.client.logout()
        self.assertEqual(self.client.get(url).status_code, 302)
        self.login('customer')
        self.assertEqual(self.client.get(url).status_code, 302)
        self.login('expert')
        self.assertEqual(self.client.get(url)['Content-Type'], 'image/png')

    def test_member_sees_only_own_bookings(self):
        self.walkin(phone='0899990000', customer_name='Someone Else')
        self.login('customer')
        res = self.client.get(reverse('website:member_dashboard'))
        self.assertNotContains(res, 'Someone Else')
        self.assertNotContains(res, 'BK-0')

    def test_staff_login_page_rejects_customer(self):
        from .base import PASSWORD
        res = self.client.post(reverse('accounts:staff_login'), {'username': '0811111111', 'password': PASSWORD})
        self.assertEqual(res.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)
        res = self.client.post(reverse('accounts:staff_login'), {'username': 'front1', 'password': PASSWORD})
        self.assertEqual(res.status_code, 302)

    def test_login_next_cannot_redirect_off_site(self):
        from .base import PASSWORD
        res = self.client.post(reverse('accounts:staff_login') + '?next=https://evil.example/',
                               {'username': 'front1', 'password': PASSWORD})
        self.assertEqual(res['Location'], bo('dashboard'))

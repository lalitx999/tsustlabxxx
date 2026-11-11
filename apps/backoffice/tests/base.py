"""Shared helpers for the back-office tests (users per role, JSON calls, sample bookings)."""
import base64
import json
import uuid
from io import BytesIO

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from PIL import Image

from apps.bookings.models import Booking
from apps.catalog.models import MembershipLevel
from apps.customers.models import Customer

PASSWORD = 'Str0ng-pass!'
STAFF = ('admin', 'manager', 'front', 'expert')


def png_data_url(color='red'):
    buffer = BytesIO()
    Image.new('RGB', (20, 20), color).save(buffer, format='PNG')
    return 'data:image/png;base64,' + base64.b64encode(buffer.getvalue()).decode()


def bo(name, *args):
    return reverse(f'backoffice:{name}', args=args)


class BackofficeTestCase(TestCase):
    """One user per role plus helpers that behave like the browser's TL.api()."""

    def setUp(self):
        User = get_user_model()
        self.users = {role: User.objects.create_user(f'{role}1', password=PASSWORD, role=role,
                                                     full_name=f'{role.title()} User')
                      for role in STAFF}
        self.member_user = User.objects.create_user('0811111111', password=PASSWORD, role='customer',
                                                    phone='0811111111')
        self.member = Customer.objects.create(user=self.member_user, full_name='Member One',
                                              phone_number='0811111111', email='member@example.com',
                                              membership_level=MembershipLevel.objects.get(level_name='Silver'))

    # ------------------------------------------------------------ requests
    def login(self, role):
        if role is None:
            self.client.logout()
        elif role == 'customer':
            self.client.force_login(self.member_user)
        else:
            self.client.force_login(self.users[role])

    def post(self, url, data=None):
        # Run on_commit hooks (Celery .delay) like a real commit would.
        with self.captureOnCommitCallbacks(execute=True):
            return self.client.post(url, json.dumps(data or {}), content_type='application/json',
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')

    def get_json(self, url):
        return self.client.get(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')

    def ok(self, response, status=200):
        self.assertEqual(response.status_code, status, response.content.decode()[:500])
        return response.json()

    # ------------------------------------------------------------ data
    def booking_payload(self, **extra):
        data = {'request_key': str(uuid.uuid4()), 'service_package': 'cert_90d', 'category': 'Bag',
                'brand': 'Chanel', 'model': 'Classic Flap', 'date': '2099-01-01', 'time_slot': '11:30 - 13:00',
                'delivery_method': 'self_pickup', 'customer_name': 'Somchai Test', 'phone': '0812345678',
                'email': 'somchai@example.com', 'payment_method': 'shop'}
        data.update(extra)
        return data

    def walkin(self, role='front', **extra):
        """Create a walk-in (booking + job) as front desk; returns (booking, job)."""
        self.login(role)
        self.ok(self.post(bo('walkin_create'), self.booking_payload(**extra)), 201)
        booking = Booking.objects.select_related('job').latest('pk')
        return booking, booking.job

    def online_booking(self, **extra):
        """Anonymous online booking through the public quote + create endpoints."""
        self.client.logout()
        data = self.booking_payload(**extra)
        data['quote_token'] = self.ok(self.post(reverse('website:booking_quote'), data))['data']['quote_token']
        self.ok(self.post(reverse('website:booking_create'), data), 201)
        return Booking.objects.latest('pk')

    def complete_job(self, job, result='authentic', code=None, role='expert'):
        self.login(role)
        body = {'status': 'completed', 'result': result}
        if code:
            body['cert_code'] = code
        return self.ok(self.post(bo('job_result', job.pk), body))

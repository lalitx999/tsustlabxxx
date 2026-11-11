"""Who may choose the membership tier used for a price."""
import json
import uuid
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.bookings.models import Booking
from apps.catalog.models import MembershipLevel
from apps.catalog.services.pricing_service import quote
from apps.customers.models import Customer

BASE = {'service_package': 'cert_90d', 'category': 'Bag', 'brand': 'Chanel'}


class TierOverrideTests(TestCase):
    def post(self, url, data):
        with self.captureOnCommitCallbacks(execute=True):
            return self.client.post(url, json.dumps(data), content_type='application/json',
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')

    def test_service_ignores_requested_tier_unless_allowed(self):
        self.assertEqual(quote({**BASE, 'membership_level': 'partner'})['total'], '3000.00')
        self.assertEqual(quote({**BASE, 'membership_level': 'partner'}, allow_tier_override=True)['total'], '1750.00')
        # Front desk (manual price allowed) may still choose the tier, as before.
        self.assertEqual(quote({**BASE, 'membership_level': 'platinum'}, allow_manual_price=True)['total'], '2350.00')

    def test_anonymous_cannot_claim_a_member_discount(self):
        data = {**BASE, 'membership_level': 'platinum', 'request_key': str(uuid.uuid4()), 'model': 'Flap',
                'date': '2099-01-01', 'time_slot': '11:30 - 13:00', 'customer_name': 'A', 'phone': '0812345678',
                'payment_method': 'shop'}
        q = self.post(reverse('website:booking_quote'), data).json()['data']
        self.assertEqual((q['member_tier'], q['total']), ('general', '3000.00'))
        data['quote_token'] = q['quote_token']
        self.assertEqual(self.post(reverse('website:booking_create'), data).status_code, 201)
        booking = Booking.objects.get()
        self.assertEqual(booking.total, '3000.00')
        self.assertIsNone(booking.customer.membership_level)  # new customer is not made Platinum

    def test_member_gets_own_tier_not_requested_one(self):
        user = get_user_model().objects.create_user('0822222222', password='Str0ng-pass!', role='customer')
        Customer.objects.create(user=user, full_name='Gold M', phone_number='0822222222',
                                membership_level=MembershipLevel.objects.get(level_name='Gold'))
        self.client.force_login(user)
        q = self.post(reverse('website:booking_quote'), {**BASE, 'membership_level': 'partner'}).json()['data']
        self.assertEqual(q['member_tier'], 'gold')
        self.assertEqual(Decimal(q['total']), Decimal('950.00') + Decimal('1200.00'))

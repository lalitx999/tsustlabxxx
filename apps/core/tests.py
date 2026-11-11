"""End-to-end business rule tests (ported scenarios from the legacy tests_workflows.py).

Run: python manage.py test --settings=config.settings.test
"""
import base64
import json
import uuid
from decimal import Decimal
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase
from django.urls import reverse
from PIL import Image

from apps.bookings.models import Booking
from apps.catalog.models import PackagePrice, PromoCode, ServicePackage
from apps.catalog.services.pricing_service import quote
from apps.core.exceptions import ServiceError
from apps.core.models import GeneratedFile
from apps.customers.models import CreditEntry, Customer
from apps.customers.services.credit_service import change_credit
from apps.inspections.models import Certificate, Job


def png_data_url(color='red'):
    buffer = BytesIO()
    Image.new('RGB', (20, 20), color).save(buffer, format='PNG')
    return 'data:image/png;base64,' + base64.b64encode(buffer.getvalue()).decode()


class Base(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user('admin1', password='Str0ng-pass!', role='admin', full_name='Admin One')
        self.front = User.objects.create_user('front1', password='Str0ng-pass!', role='front')
        self.expert = User.objects.create_user('expert1', password='Str0ng-pass!', role='expert', full_name='Expert A')

    def post(self, url, data):
        # Run transaction.on_commit hooks (Celery .delay calls) like a real commit would.
        with self.captureOnCommitCallbacks(execute=True):
            return self.client.post(url, json.dumps(data), content_type='application/json',
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')

    def get_json(self, url):
        return self.client.get(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')

    def booking_payload(self, **extra):
        data = {'request_key': str(uuid.uuid4()), 'service_package': 'cert_90d', 'category': 'Bag',
                'brand': 'Chanel', 'model': 'Classic Flap', 'date': '2099-01-01', 'time_slot': '11:30 - 13:00',
                'delivery_method': 'self_pickup', 'customer_name': 'Somchai Test', 'phone': '0812345678',
                'email': 'somchai@example.com', 'payment_method': 'shop'}
        data.update(extra)
        return data


class PricingTests(Base):
    def test_default_price_cert_90d_adds_certificate_fee(self):
        q = quote({'service_package': 'cert_90d', 'category': 'Bag', 'brand': 'Unknown Brand'})
        self.assertEqual(q['total'], '3000.00')  # 1,000 inspection + 2,000 certificate
        self.assertEqual(q['vat_amount'], '196.26')

    def test_photo_review_is_fixed_500(self):
        q = quote({'service_package': 'photo_review', 'category': 'Watch', 'brand': 'Rolex', 'delivery_method': 'shipping'})
        self.assertEqual(q['total'], '500.00')
        self.assertEqual(q['delivery_method'], 'self_pickup')

    def test_member_factor_on_package_price(self):
        PackagePrice.objects.create(package=ServicePackage.objects.get(code='cert_15d'), category='Bag',
                                    brand='Louis Vuitton', member_tier='general', amount=Decimal('2000'))
        q = quote({'service_package': 'cert_15d', 'category': 'Bag', 'brand': 'LV', 'membership_level': 'platinum'})
        self.assertEqual(q['service_amount'], '1700.00')  # alias LV + 15% off

    def test_promo_and_shipping(self):
        PromoCode.objects.create(code='SAVE100', discount_type='fixed', discount_value=Decimal('100'))
        q = quote({'service_package': 'cert_15d', 'category': 'Bag', 'brand': 'X', 'promo_code': 'save100',
                   'delivery_method': 'shipping'})
        self.assertEqual(q['service_amount'], '900.00')
        self.assertEqual(q['total'], '1000.00')  # + 100 shipping

    def test_manual_price_needs_reason(self):
        with self.assertRaises(ServiceError):
            quote({'service_package': 'cert_15d', 'category': 'Bag', 'brand': 'X', 'manual_service_amount': '10'},
                  allow_manual_price=True)


class PublicBookingTests(Base):
    def _quote(self, data):
        res = self.post(reverse('website:booking_quote'), data)
        self.assertEqual(res.status_code, 200, res.content)
        return res.json()['data']['quote_token']

    def test_public_booking_with_signed_quote_is_idempotent(self):
        data = self.booking_payload()
        data['quote_token'] = self._quote(data)
        first = self.post(reverse('website:booking_create'), data)
        self.assertEqual(first.status_code, 201, first.content)
        again = self.post(reverse('website:booking_create'), data)
        self.assertEqual(again.status_code, 200)
        self.assertEqual(Booking.objects.count(), 1)
        receipt = self.client.get(first.json()['data']['receipt_url'])
        self.assertContains(receipt, 'BK-')
        self.assertNotContains(receipt, 'Somchai')  # receipt never shows personal data

    def test_tampered_price_is_rejected(self):
        data = self.booking_payload()
        token = self._quote(data)
        data.update(quote_token=token, brand='Hermes')  # changed after quoting
        res = self.post(reverse('website:booking_create'), data)
        self.assertEqual(res.status_code, 400)

    def test_transfer_requires_slip(self):
        data = self.booking_payload(payment_method='transfer')
        data['quote_token'] = self._quote(data)
        self.assertEqual(self.post(reverse('website:booking_create'), data).status_code, 400)
        data['slip'] = png_data_url()
        res = self.post(reverse('website:booking_create'), data)
        self.assertEqual(res.status_code, 201, res.content)
        booking = Booking.objects.get()
        self.assertEqual(booking.payment_status, 'pending_review')
        self.assertTrue(booking.payment_slip.name)

    def test_photo_review_requires_photos(self):
        data = self.booking_payload(service_package='photo_review')
        data['quote_token'] = self._quote(data)
        self.assertEqual(self.post(reverse('website:booking_create'), data).status_code, 400)
        data['photos'] = [png_data_url(), png_data_url('blue')]
        self.assertEqual(self.post(reverse('website:booking_create'), data).status_code, 201)
        self.assertEqual(Booking.objects.get().photos.count(), 2)

    def test_fake_image_is_rejected(self):
        data = self.booking_payload(service_package='photo_review')
        data['quote_token'] = self._quote(data)
        data['photos'] = ['data:image/png;base64,' + base64.b64encode(b'not an image').decode()]
        self.assertEqual(self.post(reverse('website:booking_create'), data).status_code, 400)


class CounterFlowTests(Base):
    def test_walkin_inspection_certificate_and_report(self):
        self.client.force_login(self.front)
        payload = self.booking_payload(mark_paid=True, counter_method='cash', reference='RC-1', color='Black')
        res = self.post(reverse('backoffice:walkin_create'), payload)
        self.assertEqual(res.status_code, 201, res.content)
        booking = Booking.objects.get()
        job = Job.objects.get()
        self.assertEqual(booking.payment_status, 'paid')
        self.assertEqual(booking.payment_method, 'cash')
        self.assertEqual(job.queue_no, f'{booking.branch_id}-001')
        self.assertEqual(len(mail.outbox), 1)  # payment confirmation (Celery eager)

        # Front desk cannot record a result.
        self.assertEqual(self.post(reverse('backoffice:job_result', args=[job.pk]),
                                   {'status': 'completed', 'result': 'authentic'}).status_code, 403)

        self.client.force_login(self.expert)
        res = self.post(reverse('backoffice:job_result', args=[job.pk]),
                        {'status': 'completed', 'result': 'authentic', 'cert_code': 'TL-TEST-0001'})
        self.assertEqual(res.status_code, 200, res.content)
        cert = Certificate.objects.get()
        self.assertEqual(cert.cert_code, 'TL-TEST-0001')
        self.assertEqual(cert.validity_days, 90)
        self.assertEqual(len(mail.outbox), 2)  # inspection result

        verify = self.get_json(reverse('website:verify_lookup') + '?id=TL-TEST-0001')
        self.assertEqual(verify.json()['data']['status'], 'authentic')
        self.assertNotIn('Somchai', verify.content.decode())

        pdf = self.post(reverse('website:certificate_pdf', args=['TL-TEST-0001']), {})
        self.assertEqual(pdf.status_code, 200, pdf.content)
        item = GeneratedFile.objects.get(kind='certificate_pdf')
        self.assertEqual(item.status, 'ready', item.error)

        self.client.force_login(self.front)
        report = self.get_json(reverse('backoffice:report_data'))
        self.assertEqual(report.json()['data']['stats']['revenue_cash'], 3000.0)

    def test_paid_booking_cancel_needs_review_and_refund(self):
        self.client.force_login(self.front)
        self.post(reverse('backoffice:walkin_create'), self.booking_payload(mark_paid=True, reference='R'))
        booking = Booking.objects.get()
        res = self.post(reverse('backoffice:booking_cancel', args=[booking.pk]), {'reason': 'changed mind'})
        self.assertEqual(res.json()['data']['status'], 'pending')
        cancel = booking.cancellationrequest
        res = self.post(reverse('backoffice:cancellation_review', args=[cancel.pk]),
                        {'action': 'approve', 'refund_amount': '99999'})
        self.assertEqual(res.status_code, 400)  # more than paid
        self.post(reverse('backoffice:cancellation_review', args=[cancel.pk]), {'action': 'approve', 'refund_amount': '1000'})
        booking.refresh_from_db()
        self.assertEqual(booking.status, 'cancelled')
        self.assertEqual(Job.objects.get().status, 'cancelled')


class WalletTests(Base):
    def test_ledger_is_idempotent_and_never_negative(self):
        customer = Customer.objects.create(full_name='A', phone_number='0899999999')
        change_credit(customer, Decimal('500'), 'topup:1', 'test', self.admin)
        change_credit(customer, Decimal('500'), 'topup:1', 'test', self.admin)  # retry
        customer.refresh_from_db()
        self.assertEqual(customer.credit_balance, Decimal('500.00'))
        self.assertEqual(CreditEntry.objects.count(), 1)
        with self.assertRaises(ServiceError):
            change_credit(customer, Decimal('-600'), 'booking:9', 'pay', self.admin)

    def test_member_pays_with_wallet(self):
        User = get_user_model()
        user = User.objects.create_user('0811111111', password='Str0ng-pass!', role='customer')
        customer = Customer.objects.create(user=user, full_name='Member', phone_number='0811111111')
        change_credit(customer, Decimal('5000'), 'seed', 'seed', self.admin)
        self.client.force_login(user)
        data = self.booking_payload(payment_method='wallet')
        data['quote_token'] = self.post(reverse('website:booking_quote'), data).json()['data']['quote_token']
        res = self.post(reverse('website:booking_create'), data)
        self.assertEqual(res.status_code, 201, res.content)
        customer.refresh_from_db()
        self.assertEqual(customer.credit_balance, Decimal('2000.00'))


class AccessTests(Base):
    def test_backoffice_requires_staff(self):
        self.assertEqual(self.client.get(reverse('backoffice:dashboard')).status_code, 302)
        self.assertEqual(self.get_json(reverse('backoffice:booking_rows')).status_code, 401)
        self.client.force_login(self.expert)
        self.assertEqual(self.get_json(reverse('backoffice:booking_rows')).status_code, 403)
        self.assertEqual(self.client.get(reverse('backoffice:users')).status_code, 302)

    def test_member_cannot_cancel_other_booking(self):
        User = get_user_model()
        user = User.objects.create_user('0822222222', password='Str0ng-pass!', role='customer')
        Customer.objects.create(user=user, full_name='Other', phone_number='0822222222')
        self.client.force_login(self.front)
        self.post(reverse('backoffice:walkin_create'), self.booking_payload())
        self.client.force_login(user)
        booking = Booking.objects.get()
        res = self.post(reverse('website:member_cancel', args=[booking.pk]), {'reason': 'x'})
        self.assertEqual(res.status_code, 403)

    def test_all_pages_render(self):
        for name in ('home', 'about', 'services', 'process', 'verify', 'contact', 'partner', 'booking',
                     'terms', 'privacy', 'member_login', 'member_register'):
            self.assertEqual(self.client.get(reverse(f'website:{name}')).status_code, 200, name)
        self.client.force_login(self.admin)
        for name in ('dashboard', 'walkin', 'bookings', 'jobs', 'queue', 'operations', 'progress', 'completed',
                     'certificates', 'qr', 'customers', 'membership', 'inquiries', 'reports', 'analytics', 'users',
                     'pricing', 'promos', 'system'):
            self.assertEqual(self.client.get(reverse(f'backoffice:{name}')).status_code, 200, name)

    def test_contact_form(self):
        res = self.post(reverse('website:contact_submit'), {'name': 'A', 'email': 'bad', 'message': 'hi'})
        self.assertEqual(res.status_code, 400)
        res = self.post(reverse('website:contact_submit'), {'name': 'A', 'email': 'a@b.co', 'message': 'hi'})
        self.assertEqual(res.status_code, 201)

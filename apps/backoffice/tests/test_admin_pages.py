"""Membership credit, top-up review, reports, users, promo codes and pricing settings."""
import uuid
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.catalog.models import Brand, CheckoutPolicy, PackagePrice, PromoCode, ServicePackage
from apps.core.models import GeneratedFile
from apps.customers.models import CreditEntry, TopupRequest

from .base import PASSWORD, BackofficeTestCase, bo, png_data_url


class MembershipTests(BackofficeTestCase):
    def credit(self, kind, amount, key=None):
        return self.post(bo('customer_credit'), {'customer_id': self.member.pk, 'type': kind, 'amount': amount,
                                                 'reason': 'test', 'request_key': key or str(uuid.uuid4())})

    def test_admin_adds_and_deducts_credit(self):
        self.login('admin')
        key = str(uuid.uuid4())
        self.assertEqual(self.ok(self.credit('add', '500', key))['data']['credit_balance'], '500.00')
        self.ok(self.credit('add', '500', key))  # double click: same request_key, counted once
        self.assertEqual(self.ok(self.credit('deduct', '200'))['data']['credit_balance'], '300.00')
        self.assertEqual(self.credit('deduct', '1000').status_code, 400)  # never negative
        self.assertEqual(self.credit('add', '-5').status_code, 400)
        self.assertEqual(self.credit('gift', '5').status_code, 400)
        self.member.refresh_from_db()
        self.assertEqual(self.member.credit_balance, Decimal('300.00'))
        self.assertEqual(CreditEntry.objects.filter(customer=self.member).count(), 2)

    def test_credit_admin_only(self):
        for role in ('front', 'manager', 'expert'):
            self.login(role)
            self.assertEqual(self.credit('add', '100').status_code, 403, role)

    def test_topup_flow_member_to_admin(self):
        self.login('customer')
        topup_id = self.ok(self.post(reverse('website:member_topup'), {'amount': '500'}), 201)['data']['topup_id']
        self.assertEqual(self.post(reverse('website:member_topup'), {'amount': '50'}).status_code, 400)
        self.ok(self.post(reverse('website:member_topup_slip'), {'topup_id': topup_id, 'slip': png_data_url()}))
        self.login('admin')
        url = bo('topup_review', topup_id)
        self.assertEqual(self.post(url, {'action': 'approve', 'reference': 'R', 'amount': '400'}).status_code, 400)
        self.assertEqual(self.ok(self.post(url, {'action': 'approve', 'reference': 'R', 'amount': '500'}))['data']['status'],
                         'approved')
        self.ok(self.post(url, {'action': 'approve', 'reference': 'R', 'amount': '500'}))  # repeat is a no-op
        self.member.refresh_from_db()
        self.assertEqual(self.member.credit_balance, Decimal('500.00'))

    def test_topup_reject_and_without_slip(self):
        topup = TopupRequest.objects.create(customer=self.member, amount=Decimal('300'))
        self.login('admin')
        url = bo('topup_review', topup.pk)
        self.assertEqual(self.post(url, {'action': 'approve', 'reference': 'R', 'amount': '300'}).status_code, 400)
        self.ok(self.post(url, {'action': 'reject', 'reference': 'no slip'}))
        topup.refresh_from_db()
        self.assertEqual(topup.status, 'rejected')
        self.login('front')
        self.assertEqual(self.post(url, {'action': 'approve', 'reference': 'R', 'amount': '300'}).status_code, 403)

    def test_membership_page_shows_member(self):
        self.login('front')
        res = self.client.get(bo('membership'))
        self.assertContains(res, 'Member One')
        self.assertNotContains(res, 'data-bs-target="#creditModal"')  # adjust button is admin-only
        self.login('admin')
        self.assertContains(self.client.get(bo('membership')), 'data-bs-target="#creditModal"')


class ReportTests(BackofficeTestCase):
    def test_report_totals_by_method(self):
        self.walkin(mark_paid=True, counter_method='cash', reference='R1')
        self.walkin(phone='0870000001', mark_paid=True, counter_method='credit_card', reference='R2')
        self.walkin(phone='0870000002')  # unpaid -> no revenue
        self.login('manager')
        data = self.ok(self.get_json(bo('report_data')))['data']
        s = data['stats']
        self.assertEqual((s['total_jobs'], s['revenue_cash'], s['revenue_card'], s['gross_revenue']), (3, 3000.0, 3000.0, 6000.0))

    def test_period_validation(self):
        self.login('front')
        self.assertEqual(self.get_json(bo('report_data') + '?date_from=2026-02-02&date_to=2026-02-01').status_code, 400)
        self.assertEqual(self.get_json(bo('report_data') + '?date_from=bad').status_code, 400)
        data = self.ok(self.get_json(bo('report_data') + '?month=2026-02'))['data']
        self.assertEqual((data['date_from'], data['date_to']), ('2026-02-01', '2026-02-28'))

    def test_report_pdf(self):
        self.walkin(mark_paid=True, reference='R1')
        self.login('front')
        url = self.ok(self.post(bo('report_pdf'), {'date_from': '2026-01-01', 'date_to': '2026-12-31'}))['data']['status_url']
        status = self.ok(self.get_json(url))['data']
        self.assertEqual(status['status'], 'ready', status)
        res = self.client.get(status['download_url'])
        self.assertTrue(b''.join(res.streaming_content).startswith(b'%PDF'))
        # Another staff member's report file is still readable by staff; anonymous is not.
        self.client.logout()
        self.assertEqual(self.get_json(url).status_code, 403)
        item = GeneratedFile.objects.get(kind='daily_report_pdf')
        self.assertEqual(self.client.get(reverse('core:file_download', args=[item.pk])).status_code, 404)


class UserTests(BackofficeTestCase):
    def test_create_edit_deactivate(self):
        self.login('admin')
        res = self.post(bo('user_create'), {'username': 'newfront', 'role': 'front', 'password': 'Another-Str0ng-1',
                                            'full_name': 'New Front', 'is_active': True})
        user_id = self.ok(res)['data']['id']
        self.assertEqual(self.post(bo('user_create'), {'username': 'newfront', 'password': 'Another-Str0ng-1'}).status_code, 400)
        self.assertEqual(self.post(bo('user_create'), {'username': 'x2', 'password': '123'}).status_code, 400)
        self.assertEqual(self.post(bo('user_create'), {'username': 'x3', 'role': 'customer',
                                                       'password': 'Another-Str0ng-1'}).status_code, 400)
        self.ok(self.post(bo('user_save', user_id), {'role': 'expert', 'full_name': 'Now Expert'}))
        user = get_user_model().objects.get(pk=user_id)
        self.assertEqual((user.role, user.full_name), ('expert', 'Now Expert'))
        self.assertTrue(user.check_password('Another-Str0ng-1'))
        self.ok(self.post(bo('user_save', user_id), {'deactivate': True}))
        user.refresh_from_db()
        self.assertFalse(user.is_active)

    def test_admin_cannot_lock_out_self(self):
        self.login('admin')
        me = self.users['admin']
        self.assertEqual(self.post(bo('user_save', me.pk), {'deactivate': True}).status_code, 400)
        self.assertEqual(self.post(bo('user_save', me.pk), {'is_active': False}).status_code, 400)
        self.assertEqual(self.post(bo('user_save', me.pk), {'role': 'front'}).status_code, 400)
        me.refresh_from_db()
        self.assertTrue(me.is_active)
        self.assertEqual(me.role, 'admin')

    def test_admin_role_cannot_take_over_superuser_or_customer(self):
        root = get_user_model().objects.create_superuser('root', password=PASSWORD, role='admin')
        self.login('admin')
        res = self.post(bo('user_save', root.pk), {'password': 'Hijack-Str0ng-1'})
        self.assertEqual(res.status_code, 403)
        root.refresh_from_db()
        self.assertTrue(root.check_password(PASSWORD))
        self.assertEqual(self.post(bo('user_save', root.pk), {'deactivate': True}).status_code, 403)
        self.assertEqual(self.post(bo('user_save', self.member_user.pk), {'role': 'admin'}).status_code, 404)
        self.member_user.refresh_from_db()
        self.assertEqual(self.member_user.role, 'customer')
        # A real superuser may still manage it.
        self.client.force_login(root)
        self.ok(self.post(bo('user_save', root.pk), {'full_name': 'Root'}))

    def test_users_page_lists_staff_only(self):
        self.login('admin')
        res = self.client.get(bo('users'))
        self.assertContains(res, 'front1')
        self.assertNotContains(res, '0811111111')


class PromoTests(BackofficeTestCase):
    def test_create_use_and_delete(self):
        self.login('admin')
        promo_id = self.ok(self.post(bo('promo_create'), {
            'code': 'save10', 'discount_type': 'percentage', 'discount_value': '10', 'max_discount': '200',
            'min_spend': '0', 'valid_from': '', 'valid_to': '2099-12-31T23:59', 'usage_limit': '5', 'is_active': True}))['data']['id']
        promo = PromoCode.objects.get(pk=promo_id)
        self.assertEqual(promo.code, 'SAVE10')
        self.assertEqual(self.post(bo('promo_create'), {'code': 'SAVE10', 'discount_value': '1'}).status_code, 400)
        self.assertEqual(self.post(bo('promo_create'), {'code': 'P2', 'discount_type': 'percentage',
                                                        'discount_value': '150'}).status_code, 400)
        self.assertEqual(self.post(bo('promo_create'), {'code': 'P3', 'discount_value': '1', 'usage_limit': '0'}).status_code, 400)
        self.assertEqual(self.post(bo('promo_create'), {'code': 'P4', 'discount_value': '1', 'valid_to': 'soon'}).status_code, 400)
        # Editing only the value must still respect the percentage cap.
        self.assertEqual(self.post(bo('promo_save', promo_id), {'discount_value': '150'}).status_code, 400)

        # The code works on the public booking (10% capped at 200 on 3,000).
        booking = self.online_booking(promo_code='save10')
        self.assertEqual(booking.total, '2800.00')
        promo.refresh_from_db()
        self.assertEqual(promo.used_count, 1)

        # Used code: "delete" deactivates it; unused code: really deleted.
        self.login('admin')
        self.assertIn('ปิดการใช้งาน', self.ok(self.post(bo('promo_save', promo_id), {'delete': True}))['message'])
        promo.refresh_from_db()
        self.assertFalse(promo.is_active)
        other = PromoCode.objects.create(code='UNUSED', discount_value=Decimal('50'))
        self.ok(self.post(bo('promo_save', other.pk), {'delete': True}))
        self.assertFalse(PromoCode.objects.filter(pk=other.pk).exists())

    def test_expired_or_used_up_codes_are_refused(self):
        PromoCode.objects.create(code='OLD', discount_value=Decimal('100'), valid_to='2000-01-01T00:00:00Z')
        PromoCode.objects.create(code='FULL', discount_value=Decimal('100'), usage_limit=1, used_count=1)
        for code in ('OLD', 'FULL', 'NOPE'):
            res = self.post(reverse('website:booking_quote'), self.booking_payload(promo_code=code))
            self.assertEqual(res.status_code, 400, code)


class PricingSettingsTests(BackofficeTestCase):
    def save(self, body):
        return self.post(bo('pricing_save'), body)

    def test_rate_used_by_quote_then_deleted(self):
        self.login('admin')
        self.ok(self.save({'rate': {'package': 'cert_15d', 'category': 'Bag', 'brand': 'Hermes', 'member_tier': 'general',
                                    'amount': '5000'}}))
        rate = PackagePrice.objects.get()
        q = self.ok(self.post(reverse('website:booking_quote'),
                              self.booking_payload(service_package='cert_15d', brand='Hermes')))['data']
        self.assertEqual(q['total'], '5000.00')
        self.assertEqual(self.save({'rate': {'package': 'cert_15d', 'category': 'Bag', 'brand': 'Hermes',
                                             'member_tier': 'gold', 'amount': '1'}}).status_code, 400)
        self.assertEqual(self.save({'rate': {'package': 'photo_review', 'category': 'Bag', 'brand': 'X',
                                             'amount': '1'}}).status_code, 400)
        self.ok(self.save({'delete_rate_id': rate.pk}))
        self.assertFalse(PackagePrice.objects.exists())

    def test_policy_validity_and_brand(self):
        self.login('admin')
        self.ok(self.save({'policy': {'prices_include_vat': False, 'shipping_fee': '150', 'shipping_taxable': True}}))
        policy = CheckoutPolicy.objects.get(pk=1)
        self.assertEqual((policy.prices_include_vat, policy.shipping_fee, policy.shipping_taxable),
                         (False, Decimal('150.00'), True))
        self.assertEqual(self.save({'policy': {'shipping_fee': '-1'}}).status_code, 400)
        self.assertEqual(self.save({'policy': {'approved': 'yes'}}).status_code, 400)
        q = self.ok(self.post(reverse('website:booking_quote'), self.booking_payload(service_package='cert_15d')))['data']
        self.assertEqual(q['total'], '1070.00')  # VAT added on top

        self.ok(self.save({'package': {'code': 'cert_90d', 'validity_days': 120}}))
        self.assertEqual(ServicePackage.objects.get(code='cert_90d').validity_days, 120)
        self.assertEqual(self.save({'package': {'code': 'cert_90d', 'validity_days': 0}}).status_code, 400)
        self.assertEqual(self.save({'package': {'code': 'photo_review', 'validity_days': 10}}).status_code, 400)

        self.ok(self.save({'brand_name': 'Goyard'}))
        self.assertEqual(self.save({'brand_name': 'goyard'}).status_code, 400)
        brand = Brand.objects.get(brand_name='Goyard')
        self.ok(self.save({'delete_brand_id': brand.pk}))
        self.assertFalse(Brand.objects.exists())

    def test_pricing_admin_only(self):
        for role in ('front', 'manager', 'expert'):
            self.login(role)
            self.assertEqual(self.save({'brand_name': 'X'}).status_code, 403, role)


class InquiryTests(BackofficeTestCase):
    def test_status_and_delete(self):
        from apps.inquiries.models import Contact
        self.client.logout()
        self.ok(self.post(reverse('website:contact_submit'), {'name': 'A', 'email': 'a@b.co', 'message': 'hi'}), 201)
        self.ok(self.post(reverse('website:partner_submit'), {'business_name': 'Shop', 'contact_name': 'B',
                                                              'phone': '0811', 'email': 'b@b.co'}), 201)
        contact = Contact.objects.get()
        self.login('front')
        self.ok(self.post(bo('inquiry_update', 'contact', contact.pk), {'status': 'read'}))
        self.assertEqual(self.post(bo('inquiry_update', 'contact', contact.pk), {'status': 'weird'}).status_code, 400)
        self.assertEqual(self.post(bo('inquiry_update', 'other', contact.pk), {'status': 'read'}).status_code, 404)
        self.ok(self.post(bo('inquiry_update', 'contact', contact.pk), {'delete': True}))
        self.assertFalse(Contact.objects.exists())

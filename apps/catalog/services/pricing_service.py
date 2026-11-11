"""Price quote engine (ported rule-for-rule from the legacy commerce.quote).

Order of price sources for a real inspection package:
  1. manual price from the front desk (needs a reason)
  2. PackagePrice row for package/category/brand (general tier; member factor applied)
  3. BrandPricing master row (+ certificate fee for cert_90d)
  4. category default (Watch 1,500 / others 1,000; + certificate fee for cert_90d)
Photo Review is always 500. Promo code and shipping are applied afterwards.
"""
from decimal import Decimal
from functools import reduce
from operator import or_

from django.core import signing
from django.db.models import Q

from apps.catalog.models import CATEGORIES, BrandPricing, CheckoutPolicy, PackagePrice, ServicePackage
from apps.catalog.services.promo_service import check_promo_usable, promo_discount
from apps.core.exceptions import ServiceError
from apps.core.money import money

PHOTO_REVIEW_PRICE = Decimal('500.00')
QUOTE_SALT = 'checkout'
QUOTE_MAX_AGE = 1800

# Member factor applies to the inspection fee only.
MEMBER_PRICE_FACTORS = {
    'general': Decimal('1'), 'silver': Decimal('1'),
    'gold': Decimal('0.95'), '5pct': Decimal('0.95'),
    'platinum': Decimal('0.85'), '15pct': Decimal('0.85'),
}
CERT_PRICE_BY_TIER = {
    'general': Decimal('2000.00'), 'silver': Decimal('2000.00'),
    'gold': Decimal('1200.00'), 'platinum': Decimal('1500.00'), 'partner': Decimal('1000.00'),
}
BRAND_ALIASES = {
    'louis vuitton': ['lv'], 'lv': ['louis vuitton'],
    'saint laurent': ['ysl'], 'ysl': ['saint laurent'],
    'bottega veneta': ['bottega'], 'bottega': ['bottega veneta'],
    'miu miu': ['miumiu'], 'miumiu': ['miu miu'],
    'celine': ['celne'], 'celne': ['celine'],
    'max mara': ['maxmara'], 'maxmara': ['max mara'],
    'tiffany & co.': ['tiffany'], 'tiffany': ['tiffany & co.'],
}


def get_policy() -> CheckoutPolicy:
    policy, _ = CheckoutPolicy.objects.get_or_create(pk=1, defaults={
        'approved': True, 'prices_include_vat': True, 'shipping_taxable': False, 'shipping_fee': Decimal('100.00'),
    })
    return policy


def brand_candidates(brand: str) -> list:
    return [brand] + BRAND_ALIASES.get(brand.lower(), [])


def _first_by_brand(queryset, brands):
    """One query for all alias spellings; keep the caller's preference order."""
    rows = list(queryset.filter(reduce(or_, (Q(brand__iexact=b) for b in brands))))
    for wanted in brands:
        for row in rows:
            if row.brand.lower() == wanted.lower():
                return row
    return None


def resolve_tier(data: dict, customer=None, *, allow_override=False) -> str:
    """Tier used for pricing.

    Only staff may pick a tier in the request (allow_override=True). Customers and
    anonymous visitors always get the tier stored on their own customer record,
    otherwise anyone could post membership_level=platinum and pay the member price.
    """
    requested = data.get('membership_level') or data.get('membership_tier')
    if requested and allow_override:
        return str(requested).strip().lower()
    if customer is not None and customer.membership_level_id:
        return customer.membership_level.level_name.lower()
    return 'general'


def quote(data: dict, customer=None, *, allow_manual_price=False, allow_tier_override=None) -> dict:
    """Build an immutable price snapshot. Raises ServiceError for bad input.

    allow_tier_override defaults to allow_manual_price (both mean "front desk").
    """
    if allow_tier_override is None:
        allow_tier_override = allow_manual_price
    policy = get_policy()
    code = data.get('service_package')
    package = ServicePackage.objects.filter(code=code, enabled=True).first()
    if not package:
        raise ServiceError('กรุณาเลือกแพ็กเกจใหม่: 15 วัน, 90 วัน หรือ Photo Review')
    category = str(data.get('category', '')).strip().title()
    if category not in CATEGORIES:
        raise ServiceError('ประเภทสินค้าไม่ถูกต้อง')
    brand = str(data.get('brand', '')).strip()
    if not brand:
        raise ServiceError('กรุณาระบุแบรนด์')

    tier = resolve_tier(data, customer, allow_override=allow_tier_override)
    factor = MEMBER_PRICE_FACTORS.get(tier)
    cert_price = CERT_PRICE_BY_TIER.get(tier, CERT_PRICE_BY_TIER['general'])
    discount_percent = Decimal('0')
    manual_reason = ''
    has_manual = allow_manual_price and str(data.get('manual_service_amount') or '').strip() != ''

    if package.code == 'photo_review':
        amount = before_discount = PHOTO_REVIEW_PRICE
    elif has_manual:
        manual_reason = str(data.get('price_reason', '')).strip()
        if not manual_reason:
            raise ServiceError('กรุณาระบุเหตุผล / อ้างอิงราคาพิเศษหรือโปรโมชั่น')
        amount = before_discount = money(data['manual_service_amount'])
    else:
        amount, before_discount = _catalog_price(package, category, brand, tier, factor, cert_price)
        if factor is not None:
            discount_percent = (Decimal('1') - factor) * 100

    promo_code, promo_amount = '', Decimal('0.00')
    promo_input = str(data.get('promo_code') or '').strip().upper()
    if promo_input:
        promo = check_promo_usable(promo_input, amount)
        promo_code = promo.code
        promo_amount = promo_discount(promo, amount)
        amount = max(Decimal('0.00'), amount - promo_amount)

    delivery = data.get('delivery_method') or 'self_pickup'
    if delivery not in ('self_pickup', 'shipping'):
        raise ServiceError('วิธีรับคืนไม่ถูกต้อง')
    if package.code == 'photo_review':
        delivery = 'self_pickup'
    shipping = policy.shipping_fee if delivery == 'shipping' else Decimal('0')
    taxable = amount + (shipping if policy.shipping_taxable else Decimal('0'))
    if policy.prices_include_vat:
        vat = money(taxable * Decimal('7') / Decimal('107'))
        total = money(amount + shipping)
    else:
        vat = money(taxable * Decimal('0.07'))
        total = money(amount + shipping + vat)

    return {
        'service_package': package.code,
        'validity_days': package.validity_days if package.code != 'photo_review' else 0,
        'category': category, 'brand': brand, 'member_tier': tier,
        'service_amount_before_discount': str(money(before_discount)),
        'member_discount_percent': str(money(discount_percent)),
        'member_discount_amount': str(money(before_discount - (amount + promo_amount))),
        'promo_code': promo_code,
        'promo_discount_amount': str(money(promo_amount)),
        'service_amount': str(money(amount)),
        'shipping_fee': str(money(shipping)),
        'vat_amount': str(vat),
        'subtotal': str(money(total - vat)),
        'total': str(total),
        'currency': 'THB',
        'prices_include_vat': policy.prices_include_vat,
        'delivery_method': delivery,
        'price_reason': manual_reason,
        'policy_version': policy.updated_at.isoformat(),
    }


def _catalog_price(package, category, brand, tier, factor, cert_price):
    """Return (amount, amount_before_member_discount) from the price tables."""
    pricing_tier = 'general' if factor is not None else tier
    brands = brand_candidates(brand)
    rates = PackagePrice.objects.filter(package=package, category__iexact=category)
    rate = _first_by_brand(rates.filter(member_tier__iexact=pricing_tier), brands)
    if tier == 'corporate' and not rate:
        raise ServiceError('ยังไม่ได้กำหนดราคา Corporate สำหรับบริการและสินค้านี้ กรุณาตั้งราคา Corporate แยกใน Services & Pricing')
    if not rate and pricing_tier != 'general':
        rate = _first_by_brand(rates.filter(member_tier='general'), brands)
    if rate:
        amount = money(rate.amount * factor) if factor is not None else rate.amount
        return amount, rate.amount

    master = _first_by_brand(BrandPricing.objects.filter(category__iexact=category), brands) \
        or _first_by_brand(BrandPricing.objects.all(), brands)
    if master:
        base = Decimal(str(master.partner_price if tier == 'partner' else master.base_price))
    else:
        base = Decimal('1500.00') if category == 'Watch' else Decimal('1000.00')
        if tier == 'partner':
            base = money(base * Decimal('0.75'))
    inspection = money(base * factor) if factor is not None else base
    if package.code == 'cert_90d':
        return inspection + cert_price, base + cert_price
    return inspection, base


def sign_quote(snapshot: dict, customer=None) -> str:
    return signing.dumps({'quote': snapshot, 'customer_id': customer.pk if customer else None}, salt=QUOTE_SALT)


def verify_quote(token, snapshot: dict, customer=None) -> None:
    """The customer must pay exactly what they were shown (and recently)."""
    try:
        value = signing.loads(token, salt=QUOTE_SALT, max_age=QUOTE_MAX_AGE)
    except (signing.BadSignature, TypeError):
        raise ServiceError('ใบเสนอราคาหมดอายุ กรุณาคำนวณยอดใหม่')
    if value != {'quote': snapshot, 'customer_id': customer.pk if customer else None}:
        raise ServiceError('ราคาหรือข้อมูลเปลี่ยน กรุณาคำนวณยอดและตรวจสอบใหม่ก่อนชำระ')


def load_signed_quote(token) -> dict:
    try:
        return signing.loads(token, salt=QUOTE_SALT, max_age=QUOTE_MAX_AGE)['quote']
    except (signing.BadSignature, TypeError, KeyError):
        raise ServiceError('กรุณาคำนวณยอดใหม่ก่อนสร้าง QR')

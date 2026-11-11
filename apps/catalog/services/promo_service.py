from decimal import Decimal

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from apps.catalog.models import PromoCode
from apps.core.exceptions import ServiceError
from apps.core.money import money


def check_promo_usable(code: str, amount: Decimal | None = None) -> PromoCode:
    promo = PromoCode.objects.filter(code__iexact=code.strip(), is_active=True).first()
    if not promo:
        raise ServiceError('โค้ดส่วนลดไม่ถูกต้องหรือถูกยกเลิกแล้ว')
    now = timezone.now()
    if promo.valid_from and now < promo.valid_from:
        raise ServiceError('โค้ดส่วนลดนี้ยังไม่ถึงช่วงเวลาใช้งาน')
    if promo.valid_to and now > promo.valid_to:
        raise ServiceError('โค้ดส่วนลดนี้หมดอายุแล้ว')
    if promo.usage_limit is not None and promo.used_count >= promo.usage_limit:
        raise ServiceError('โค้ดส่วนลดนี้ถูกใช้งานครบตามจำนวนสิทธิ์แล้ว')
    if amount is not None and promo.min_spend and amount < promo.min_spend:
        raise ServiceError(f'โค้ดส่วนลดนี้ใช้ได้เมื่อมียอดขั้นต่ำ {promo.min_spend:,.2f} บาท')
    return promo


def promo_discount(promo: PromoCode, amount: Decimal) -> Decimal:
    if promo.discount_type == 'fixed':
        discount = min(promo.discount_value, amount)
    else:
        discount = amount * promo.discount_value / Decimal('100')
        if promo.max_discount and discount > promo.max_discount:
            discount = promo.max_discount
    return money(discount)


def consume_promo(code: str) -> PromoCode | None:
    """Count one use atomically (F expression avoids lost updates)."""
    if not code:
        return None
    promo = PromoCode.objects.filter(code__iexact=code).first()
    if promo:
        PromoCode.objects.filter(pk=promo.pk).update(used_count=F('used_count') + 1)
    return promo


PROMO_FIELDS = ('code', 'description', 'discount_type', 'discount_value', 'min_spend', 'max_discount',
                'valid_from', 'valid_to', 'usage_limit', 'is_active')


def _clean_promo_data(data: dict) -> dict:
    from django.utils.dateparse import parse_datetime

    cleaned = {}
    if 'code' in data:
        code = str(data['code']).strip().upper()
        if not code or len(code) > 50:
            raise ServiceError('กรุณาระบุโค้ด (ไม่เกิน 50 ตัวอักษร)')
        cleaned['code'] = code
    if 'description' in data:
        cleaned['description'] = str(data['description'] or '').strip()[:255]
    if 'discount_type' in data:
        if data['discount_type'] not in ('fixed', 'percentage'):
            raise ServiceError('ประเภทส่วนลดไม่ถูกต้อง')
        cleaned['discount_type'] = data['discount_type']
    for field in ('discount_value', 'min_spend'):
        if field in data:
            value = money(data[field] or 0)
            if value < 0:
                raise ServiceError('จำนวนเงินต้องไม่ติดลบ')
            cleaned[field] = value
    if 'max_discount' in data:
        cleaned['max_discount'] = money(data['max_discount']) if str(data['max_discount'] or '').strip() else None
    for field in ('valid_from', 'valid_to'):
        if field in data:
            raw = str(data[field] or '').strip()
            value = parse_datetime(raw) if raw else None
            if raw and value is None:
                raise ServiceError('รูปแบบวันที่ไม่ถูกต้อง')
            if value is not None and timezone.is_naive(value):
                value = timezone.make_aware(value)
            cleaned[field] = value
    if 'usage_limit' in data:
        raw = str(data['usage_limit'] or '').strip()
        try:
            cleaned['usage_limit'] = int(raw) if raw else None
        except ValueError:
            raise ServiceError('จำนวนสิทธิ์ต้องเป็นตัวเลข')
    if 'is_active' in data:
        cleaned['is_active'] = bool(data['is_active'])
    if cleaned.get('discount_type') == 'percentage' and cleaned.get('discount_value', 0) > 100:
        raise ServiceError('ส่วนลดเปอร์เซ็นต์ต้องไม่เกิน 100')
    return cleaned


@transaction.atomic
def save_promo(data: dict, promo: PromoCode | None = None) -> PromoCode:
    cleaned = _clean_promo_data(data)
    code = cleaned.get('code')
    if code and PromoCode.objects.filter(code__iexact=code).exclude(pk=getattr(promo, 'pk', None)).exists():
        raise ServiceError('โค้ดนี้มีอยู่แล้ว')
    if promo is not None:
        # An edit may send only one of the two fields; check the combination that will be saved.
        kind = cleaned.get('discount_type', promo.discount_type)
        if kind == 'percentage' and cleaned.get('discount_value', promo.discount_value) > 100:
            raise ServiceError('ส่วนลดเปอร์เซ็นต์ต้องไม่เกิน 100')
    if cleaned.get('usage_limit') is not None and cleaned['usage_limit'] < 1:
        raise ServiceError('จำนวนสิทธิ์ต้องมากกว่า 0')
    if promo is None:
        if 'code' not in cleaned or 'discount_value' not in cleaned:
            raise ServiceError('กรุณาระบุโค้ดและมูลค่าส่วนลด')
        return PromoCode.objects.create(**cleaned)
    for field, value in cleaned.items():
        setattr(promo, field, value)
    promo.save()
    return promo


def delete_promo(promo: PromoCode) -> str:
    """Used codes are deactivated (kept for history); unused codes are deleted."""
    if promo.used_count > 0:
        PromoCode.objects.filter(pk=promo.pk).update(is_active=False)
        return 'deactivated'
    promo.delete()
    return 'deleted'

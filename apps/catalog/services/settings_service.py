"""Admin: checkout policy, package price table, package validity."""
from django.db import transaction

from apps.catalog.models import CATEGORIES, Brand, PackagePrice, ServicePackage
from apps.catalog.services.pricing_service import MEMBER_PRICE_FACTORS, get_policy
from apps.core.exceptions import ServiceError
from apps.core.money import money


@transaction.atomic
def update_policy(data: dict):
    policy = get_policy()
    for field in ('approved', 'prices_include_vat', 'shipping_taxable'):
        if field in data:
            if not isinstance(data[field], bool):
                raise ServiceError('ค่าการตั้งค่าไม่ถูกต้อง')
            setattr(policy, field, data[field])
    if 'shipping_fee' in data:
        fee = money(data['shipping_fee'])
        if fee < 0:
            raise ServiceError('ค่าส่งต้องไม่ติดลบ')
        policy.shipping_fee = fee
    policy.save()
    return policy


@transaction.atomic
def save_rate(data: dict) -> PackagePrice:
    package = ServicePackage.objects.filter(code=data.get('package')).first()
    if not package:
        raise ServiceError('ไม่พบแพ็กเกจ')
    if package.code == 'photo_review':
        raise ServiceError('Photo Review ใช้ราคา 500 คงที่')
    amount = money(data.get('amount'))
    category = data.get('category')
    brand = str(data.get('brand', '')).strip()
    if amount < 0 or category not in CATEGORIES or not brand:
        raise ServiceError('ราคา ประเภท หรือแบรนด์ไม่ถูกต้อง')
    tier = str(data.get('member_tier') or 'general').strip().lower()
    if tier in MEMBER_PRICE_FACTORS and tier != 'general':
        raise ServiceError('กรุณาแก้ราคาทั่วไป: Silver ราคาเท่าทั่วไป, Gold ลด 5%, Platinum ลด 15% อัตโนมัติ')
    rate, _ = PackagePrice.objects.update_or_create(
        package=package, category=category, brand=brand, member_tier=tier, defaults={'amount': amount})
    return rate


def delete_rate(rate_id) -> None:
    PackagePrice.objects.filter(pk=rate_id).delete()


@transaction.atomic
def set_package_validity(code: str, days) -> ServicePackage:
    package = ServicePackage.objects.select_for_update().filter(code=code).first()
    if not package:
        raise ServiceError('ไม่พบแพ็กเกจ')
    if package.code == 'photo_review' or not isinstance(days, int) or not 1 <= days <= 365:
        raise ServiceError('อายุรับรองต้องเป็นจำนวนวัน 1–365 สำหรับแพ็กเกจตรวจจริง')
    package.validity_days = days
    package.save(update_fields=['validity_days'])
    return package


def add_brand(name: str) -> Brand:
    name = str(name or '').strip()
    if not name or len(name) > 100:
        raise ServiceError('กรุณาระบุชื่อแบรนด์ (ไม่เกิน 100 ตัวอักษร)')
    if Brand.objects.filter(brand_name__iexact=name).exists():
        raise ServiceError('มีแบรนด์นี้อยู่แล้ว')
    return Brand.objects.create(brand_name=name)


def delete_brand(brand_id) -> None:
    Brand.objects.filter(pk=brand_id).delete()

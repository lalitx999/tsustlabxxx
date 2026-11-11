from apps.catalog.models import Brand, MembershipLevel, PackagePrice, PromoCode, ServicePackage
from apps.catalog.services.pricing_service import MEMBER_PRICE_FACTORS


def enabled_packages():
    return list(ServicePackage.objects.filter(enabled=True).values('code', 'name', 'validity_days'))


def all_packages():
    return list(ServicePackage.objects.values('code', 'name', 'validity_days', 'enabled', 'sort_order'))


def brand_names():
    return list(Brand.objects.order_by('brand_name').values_list('brand_name', flat=True))


def membership_levels():
    return list(MembershipLevel.objects.order_by('certificate_price').values(
        'id', 'level_name', 'level_type', 'entry_requirement', 'discount_pct', 'certificate_price',
        'general_benefits', 'priority_service', 'validity_period'))


def editable_rates():
    """General-tier rates (member tiers are derived) plus special tiers like corporate."""
    member_tiers = [t for t in MEMBER_PRICE_FACTORS if t != 'general']
    return list(
        PackagePrice.objects.exclude(member_tier__in=member_tiers)
        .order_by('package_id', 'category', 'brand')
        .values('id', 'package_id', 'category', 'brand', 'member_tier', 'amount')
    )


def promo_codes():
    return list(PromoCode.objects.order_by('-created_at').values(
        'id', 'code', 'description', 'discount_type', 'discount_value', 'min_spend', 'max_discount',
        'valid_from', 'valid_to', 'usage_limit', 'used_count', 'is_active', 'created_at'))

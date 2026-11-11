from decimal import Decimal

from django.db import models

CATEGORY_CHOICES = [
    ('Bag', 'Bag'),
    ('Clothes', 'Clothes'),
    ('Shoes', 'Shoes'),
    ('Accessories', 'Accessories'),
    ('Watch', 'Watch'),
]
CATEGORIES = tuple(code for code, _ in CATEGORY_CHOICES)

SERVICE_PACKAGE_CHOICES = [
    ('cert_15d', 'ตรวจสอบ + ใบรับรอง 15 วัน'),
    ('cert_90d', 'ตรวจสอบ + ใบรับรอง 90 วัน'),
    ('photo_review', 'ตรวจสอบผ่านรูปภาพ (Photo Review)'),
]


class Brand(models.Model):
    brand_name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'brands'

    def __str__(self):
        return self.brand_name


class MembershipLevel(models.Model):
    level_name = models.CharField(max_length=50, unique=True)  # General, Silver, Gold, Platinum, Partner
    level_type = models.CharField(max_length=50)
    entry_requirement = models.TextField()
    discount_pct = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    certificate_price = models.DecimalField(max_digits=10, decimal_places=2)
    general_benefits = models.TextField(null=True, blank=True)
    priority_service = models.TextField(null=True, blank=True)
    validity_period = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        db_table = 'membership_levels'

    def __str__(self):
        return self.level_name


class BrandPricing(models.Model):
    WATCH_TIERS = [('Masterpiece', 'Masterpiece'), ('Luxury', 'Luxury'), ('Premium', 'Premium')]

    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    tier = models.CharField(max_length=20, choices=WATCH_TIERS, null=True, blank=True)
    brand = models.CharField(max_length=100)
    base_price = models.DecimalField(max_digits=10, decimal_places=2)
    price_5pct = models.DecimalField(max_digits=10, decimal_places=2)
    price_15pct = models.DecimalField(max_digits=10, decimal_places=2)
    partner_price = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'brand_pricing'
        unique_together = ('category', 'tier', 'brand')

    def __str__(self):
        tier = f' ({self.tier})' if self.tier else ''
        return f'{self.brand} - {self.category}{tier}'


class ServiceType(models.Model):
    service_name = models.CharField(max_length=100, unique=True)
    service_name_th = models.CharField(max_length=100, blank=True, null=True)
    description = models.TextField()
    price_note = models.TextField()

    class Meta:
        db_table = 'service_types'

    def __str__(self):
        return self.service_name


class ServicePackage(models.Model):
    code = models.CharField(max_length=20, primary_key=True, choices=SERVICE_PACKAGE_CHOICES)
    name = models.CharField(max_length=100)
    validity_days = models.PositiveIntegerField(default=0)
    sort_order = models.PositiveIntegerField(default=0)
    enabled = models.BooleanField(default=True)

    class Meta:
        db_table = 'api_servicepackage'
        ordering = ['sort_order']

    def __str__(self):
        return self.name


class PackagePrice(models.Model):
    package = models.ForeignKey(ServicePackage, on_delete=models.PROTECT)
    category = models.CharField(max_length=20)
    brand = models.CharField(max_length=100)
    member_tier = models.CharField(max_length=50, default='general')
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = 'api_packageprice'
        constraints = [
            models.UniqueConstraint(fields=['package', 'category', 'brand', 'member_tier'], name='unique_package_rate'),
            models.CheckConstraint(condition=models.Q(amount__gte=0), name='package_rate_nonnegative'),
        ]


class CheckoutPolicy(models.Model):
    approved = models.BooleanField(default=False)
    prices_include_vat = models.BooleanField(default=True)
    shipping_taxable = models.BooleanField(default=True)
    shipping_fee = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'api_checkoutpolicy'


class PromoCode(models.Model):
    DISCOUNT_TYPE_CHOICES = [('fixed', 'Fixed Amount (THB)'), ('percentage', 'Percentage (%)')]

    code = models.CharField(max_length=50, unique=True, db_index=True)
    description = models.CharField(max_length=255, blank=True, default='')
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPE_CHOICES, default='fixed')
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    min_spend = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    max_discount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    valid_from = models.DateTimeField(null=True, blank=True)
    valid_to = models.DateTimeField(null=True, blank=True)
    usage_limit = models.IntegerField(null=True, blank=True)
    used_count = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'promo_codes'
        ordering = ['-created_at']

    def __str__(self):
        return self.code

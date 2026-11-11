from decimal import Decimal

from django.conf import settings
from django.db import models


class Customer(models.Model):
    ACCOUNT_TYPE_CHOICES = [('standard', 'Standard'), ('corporate', 'Corporate')]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True,
                                related_name='customer_profile')
    full_name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=20, unique=True)
    line_id = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    membership_level = models.ForeignKey('catalog.MembershipLevel', on_delete=models.SET_NULL, null=True)
    credit_balance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPE_CHOICES, default='standard')
    postpaid_enabled = models.BooleanField(default=False)
    credit_limit = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    note = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'customers'

    def __str__(self):
        return f'{self.full_name} ({self.phone_number})'

    @property
    def tier_name(self):
        return self.membership_level.level_name if self.membership_level_id else 'General'


class CreditEntry(models.Model):
    """Append-only wallet ledger. Every balance change writes one row."""
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name='credit_entries')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    balance_after = models.DecimalField(max_digits=12, decimal_places=2)
    reference = models.CharField(max_length=120, unique=True)
    reason = models.TextField()
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'api_creditentry'


class TopupRequest(models.Model):
    STATUS_CHOICES = [('pending', 'Pending Approval'), ('approved', 'Approved'), ('rejected', 'Rejected')]

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='topup_requests')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(max_length=50, default='promptpay')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    evidence = models.TextField(blank=True, default='')
    slip_photo = models.ImageField(upload_to='slips/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = 'topup_requests'

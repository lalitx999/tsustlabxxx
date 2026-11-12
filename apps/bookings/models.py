from decimal import Decimal

from django.conf import settings
from django.db import models


class Booking(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    ]
    DELIVERY_METHOD_CHOICES = [('self_pickup', 'มารับด้วยตัวเอง'), ('shipping', 'จัดส่งพัสดุ')]
    PAYMENT_STATUS_LABELS = {
        'unpaid': 'ยังไม่ชำระ', 'pending_review': 'รอตรวจสลิป', 'paid': 'ชำระแล้ว',
        'rejected': 'สลิปไม่ผ่าน', 'invoiced': 'วางบิล',
    }

    customer = models.ForeignKey('customers.Customer', on_delete=models.CASCADE, related_name='bookings')
    branch = models.ForeignKey('accounts.Branch', on_delete=models.PROTECT)
    booking_date = models.DateField()
    booking_time = models.TimeField()
    service_type = models.ForeignKey('catalog.ServiceType', on_delete=models.PROTECT)
    category = models.CharField(max_length=50, blank=True, default='BAG')
    brand_name = models.CharField(max_length=100, blank=True, default='')
    model = models.CharField(max_length=100, blank=True, default='')
    note = models.TextField(blank=True, default='')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    service_package = models.CharField(max_length=20, blank=True, default='')
    price_snapshot = models.JSONField(default=dict, blank=True)
    promo_code = models.ForeignKey('catalog.PromoCode', on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='bookings')
    promo_code_str = models.CharField(max_length=50, blank=True, default='')
    payment_status = models.CharField(max_length=20, default='unpaid')
    payment_method = models.CharField(max_length=20, blank=True, default='')
    payment_evidence = models.TextField(blank=True, default='')
    # New: slip stored as a file. Legacy rows keep base64 in payment_evidence.
    payment_slip = models.ImageField(upload_to='slips/bookings/%Y/%m/', blank=True)
    CHANNEL_CHOICES = [('online', 'Online booking'), ('walk_in', 'Walk-in')]
    channel = models.CharField(max_length=10, choices=CHANNEL_CHOICES, default='online')
    request_fingerprint = models.CharField(max_length=64, blank=True, default='')
    request_key = models.UUIDField(null=True, blank=True, unique=True)
    delivery_method = models.CharField(max_length=20, choices=DELIVERY_METHOD_CHOICES, default='self_pickup')
    shipping_fee = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0.00'))
    return_address_name = models.CharField(max_length=255, blank=True, default='')
    return_phone = models.CharField(max_length=20, blank=True, default='')
    return_address_detail = models.TextField(blank=True, default='')
    return_subdistrict = models.CharField(max_length=100, blank=True, default='')
    return_district = models.CharField(max_length=100, blank=True, default='')
    return_province = models.CharField(max_length=100, blank=True, default='')
    return_postal_code = models.CharField(max_length=10, blank=True, default='')
    cancel_reason = models.TextField(blank=True, null=True)
    cancelled_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='cancelled_bookings')
    cancelled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'bookings'
        indexes = [
            models.Index(fields=['booking_date'], name='booking_date_idx'),
            models.Index(fields=['status', '-created_at'], name='booking_status_created_idx'),
            models.Index(fields=['payment_status'], name='booking_payment_status_idx'),
        ]

    def __str__(self):
        return f'Booking #{self.pk}'

    @property
    def display_id(self):
        return f'BK-{self.pk:04d}'

    @property
    def total(self):
        return (self.price_snapshot or {}).get('total', '0.00')

    @property
    def payment_status_label(self):
        return self.PAYMENT_STATUS_LABELS.get(self.payment_status, self.payment_status)


class BookingPhoto(models.Model):
    TYPE_CHOICES = [('customer', 'Customer'), ('staff', 'Staff')]

    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='photos')
    photo = models.ImageField(upload_to='booking_photos/%Y/%m/%d/')
    photo_type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='staff')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'booking_photos'


class CancellationRequest(models.Model):
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE)
    reason = models.TextField()
    status = models.CharField(max_length=20, default='pending')
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='cancellation_requests')
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='cancellation_reviews')
    refund_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    refund_status = models.CharField(max_length=20, default='not_required')
    refund_reference = models.CharField(max_length=255, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'api_cancellationrequest'


class TaxDocument(models.Model):
    """A receipt or tax invoice issued for a paid booking. Numbers are fixed once issued."""
    RECEIPT = 'receipt'
    TAX_INVOICE = 'tax_invoice'
    TYPE_CHOICES = [
        (RECEIPT, 'ใบกำกับภาษีอย่างย่อ / ใบเสร็จรับเงิน'),
        (TAX_INVOICE, 'ใบกำกับภาษี'),
    ]
    PREFIX = {RECEIPT: 'RC', TAX_INVOICE: 'INV'}

    booking = models.ForeignKey(Booking, on_delete=models.PROTECT, related_name='tax_documents')
    doc_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    number = models.CharField(max_length=30, unique=True)
    buyer_name = models.CharField(max_length=255, blank=True, default='')
    buyer_tax_id = models.CharField(max_length=20, blank=True, default='')
    buyer_branch = models.CharField(max_length=100, blank=True, default='')
    buyer_address = models.TextField(blank=True, default='')
    amounts = models.JSONField(default=dict)
    issued_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                  related_name='issued_tax_documents')
    issued_at = models.DateTimeField(auto_now_add=True)
    voided_at = models.DateTimeField(null=True, blank=True)
    voided_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                  related_name='voided_tax_documents')
    void_reason = models.TextField(blank=True, default='')

    class Meta:
        db_table = 'tax_documents'
        constraints = [
            models.UniqueConstraint(fields=['booking', 'doc_type'], condition=models.Q(voided_at__isnull=True),
                                    name='one_active_tax_document_per_type'),
        ]

    def __str__(self):
        return self.number

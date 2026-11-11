from decimal import Decimal

from django.conf import settings
from django.db import models

from apps.catalog.models import SERVICE_PACKAGE_CHOICES


class Job(models.Model):
    """An item received at the counter and inspected by an expert.

    Price/VAT syncing that used to live in save() is now in
    apps.inspections.services.job_service.set_job_price().
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    RESULT_CHOICES = [('authentic', 'Authentic'), ('fake', 'Fake'), ('inconclusive', 'Inconclusive')]
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('credit_card', 'Credit Card'),
        ('transfer', 'Bank Transfer'),
        ('promptpay', 'PromptPay QR'),
        ('postpaid', 'Corporate Postpaid'),
    ]
    PAYMENT_STATUS_CHOICES = [('unpaid', 'Unpaid'), ('paid', 'Paid'), ('invoiced', 'Invoiced (Postpaid)')]
    SHIPPING_STATUS_CHOICES = [
        ('not_applicable', 'มารับเอง'),
        ('pending_return', 'รอจัดส่งคืน'),
        ('ready_to_ship', 'เตรียมจัดส่งแล้ว'),
        ('shipped', 'จัดส่งแล้ว'),
        ('delivered', 'ลูกค้ารับแล้ว'),
    ]

    booking = models.OneToOneField('bookings.Booking', on_delete=models.CASCADE, null=True, blank=True)
    customer = models.ForeignKey('customers.Customer', on_delete=models.CASCADE)
    category = models.CharField(max_length=50)
    brand = models.CharField(max_length=100)
    sub_category = models.CharField(max_length=100, blank=True, null=True)
    model = models.CharField(max_length=100)
    color = models.CharField(max_length=50)
    material = models.CharField(max_length=100, blank=True, default='')
    serial_number = models.CharField(max_length=100, blank=True, null=True)
    accessories = models.TextField(blank=True)
    notes = models.TextField(blank=True, null=True)
    expert_instruction = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    result = models.CharField(max_length=20, choices=RESULT_CHOICES, blank=True, null=True)
    queue_no = models.CharField(max_length=20)
    price_snapshot = models.JSONField(default=dict, blank=True)
    tag_code = models.CharField(max_length=100, blank=True, default='')
    result_recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
                                           blank=True, related_name='recorded_jobs')
    expert_source = models.CharField(max_length=255, blank=True, default='')
    service_package = models.CharField(max_length=20, choices=SERVICE_PACKAGE_CHOICES, default='cert_90d')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='unpaid')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    vat_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    express_service = models.BooleanField(default=False)
    shipping_status = models.CharField(max_length=20, choices=SHIPPING_STATUS_CHOICES, default='not_applicable')
    tracking_number = models.CharField(max_length=100, blank=True, null=True)
    cancel_reason = models.TextField(blank=True, null=True)
    cancelled_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='cancelled_jobs')
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancel_approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
                                           blank=True, related_name='approved_cancellations')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'jobs'
        indexes = [
            models.Index(fields=['status', '-created_at'], name='job_status_created_idx'),
            models.Index(fields=['created_at'], name='job_created_idx'),
        ]

    def __str__(self):
        return f'Job #{self.pk} ({self.queue_no})'

    @property
    def display_id(self):
        created = self.created_at
        prefix = f'TL{created:%y%m}' if created else 'TL'
        return f'{prefix}-{self.booking_id or 0}-{self.pk:04d}'


class Certificate(models.Model):
    STATUS_CHOICES = [
        ('authentic', 'Authentic'),
        ('unauthentic', 'Unauthentic'),
        ('revoked', 'Revoked'),
        ('expired', 'Expired'),
    ]

    job = models.OneToOneField(Job, on_delete=models.CASCADE, related_name='certificate')
    expires_at = models.DateTimeField(null=True, blank=True)
    validity_days = models.PositiveIntegerField(null=True, blank=True)
    cert_code = models.CharField(max_length=50, unique=True, blank=True, null=True)
    cert_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='authentic')
    revoke_reason = models.TextField(blank=True, null=True)
    expired_at = models.DateTimeField(null=True, blank=True)
    selected_photos = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'certificates'

    def __str__(self):
        return self.cert_code or f'Certificate #{self.pk}'


class CertificateSendLog(models.Model):
    SEND_METHOD = [('email', 'Email'), ('line', 'LINE OA')]

    certificate = models.ForeignKey(Certificate, on_delete=models.CASCADE, related_name='send_logs')
    method = models.CharField(max_length=10, choices=SEND_METHOD)
    recipient = models.CharField(max_length=255)
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'certificate_send_logs'

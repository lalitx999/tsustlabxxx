from django.db.models import Q
from django.utils import timezone

from apps.inspections.models import Certificate, Job

JOB_RELATED = ('customer', 'booking__branch', 'certificate', 'result_recorded_by')


def job_list(*, status=None, query=None, shipping=None, limit=300):
    queryset = Job.objects.select_related(*JOB_RELATED).order_by('-created_at')
    if status:
        queryset = queryset.filter(status__in=status if isinstance(status, (list, tuple)) else [status])
    if shipping:
        queryset = queryset.filter(shipping_status__in=shipping)
    if query:
        query = query.strip()
        queryset = queryset.filter(
            Q(customer__full_name__icontains=query) | Q(customer__phone_number__contains=query)
            | Q(brand__icontains=query) | Q(model__icontains=query) | Q(queue_no__icontains=query)
            | Q(tag_code__icontains=query) | Q(certificate__cert_code__icontains=query))
    return queryset[:limit]


def today_queue():
    return (Job.objects.select_related('customer', 'booking')
            .filter(created_at__date=timezone.localdate()).exclude(status='cancelled').order_by('queue_no'))


def job_detail(job_id):
    return (Job.objects.select_related(*JOB_RELATED, 'booking__customer')
            .prefetch_related('booking__photos').filter(pk=job_id).first())


def find_certificate(code_or_id):
    """By cert_code (with or without TL- prefix), 'bookingId-queueNo' link, or numeric id."""
    value = str(code_or_id or '').strip()
    if not value:
        return None
    base = Certificate.objects.select_related('job__booking__branch', 'job__customer')
    cert = base.filter(cert_code__iexact=value).first()
    if cert:
        return cert
    if not value.upper().startswith('TL-'):
        cert = base.filter(cert_code__iexact=f'TL-{value}').first()
        if cert:
            return cert
        if '-' in value:
            booking_id, queue_no = value.split('-', 1)
            if booking_id.isdigit():
                cert = base.filter(job__booking_id=int(booking_id), job__queue_no=queue_no).first()
                if cert:
                    return cert
    return base.filter(pk=int(value)).first() if value.isdigit() else None


def certificate_list(*, query=None, status=None, limit=300):
    queryset = Certificate.objects.select_related('job__customer').order_by('-created_at')
    if status:
        queryset = queryset.filter(cert_status=status)
    if query:
        queryset = queryset.filter(Q(cert_code__icontains=query) | Q(job__brand__icontains=query)
                                   | Q(job__model__icontains=query) | Q(job__customer__full_name__icontains=query))
    return queryset[:limit]


def serialize_job(job: Job) -> dict:
    cert = getattr(job, 'certificate', None)
    return {
        'id': job.pk,
        'display_id': job.display_id,
        'queue_no': job.queue_no,
        'booking_id': job.booking_id,
        'customer_name': job.customer.full_name,
        'customer_phone': job.customer.phone_number,
        'category': job.category,
        'brand': job.brand,
        'model': job.model,
        'color': job.color,
        'material': job.material,
        'serial_number': job.serial_number or '',
        'accessories': job.accessories,
        'notes': job.notes or '',
        'expert_instruction': job.expert_instruction or '',
        'tag_code': job.tag_code,
        'status': job.status,
        'status_label': job.get_status_display(),
        'result': job.result or '',
        'expert_source': job.expert_source,
        'service_package': job.service_package,
        'payment_status': job.payment_status,
        'price': str(job.price),
        'shipping_status': job.shipping_status,
        'shipping_status_label': job.get_shipping_status_display(),
        'tracking_number': job.tracking_number or '',
        'certificate_code': cert.cert_code if cert else '',
        'source': job.booking.channel if job.booking_id else 'walk_in',
        'certificate_status': cert.cert_status if cert else '',
        'created_at': job.created_at.isoformat(),
    }


def serialize_certificate_public(cert: Certificate) -> dict:
    """Public verify page: product facts only, no customer data."""
    job = cert.job
    now = timezone.now()
    status = cert.cert_status
    if status == 'authentic' and cert.expires_at and now >= cert.expires_at:
        status = 'expired'
    photo_ids = cert.selected_photos or []
    photos = []
    if job.booking_id:
        by_id = {p.pk: p for p in job.booking.photos.all()}
        chosen = [by_id[i] for i in photo_ids if i in by_id] or list(by_id.values())[:4]
        photos = [p.photo.url for p in chosen if p.photo]
    return {
        'certificate_id': cert.cert_code,
        'status': status,
        'result': job.result or '',
        'brand': job.brand,
        'model': job.model,
        'category': job.category,
        'color': job.color,
        'material': job.material,
        'serial_number': job.serial_number or '',
        'issue_date': timezone.localtime(cert.created_at).date().isoformat(),
        'expire_date': timezone.localtime(cert.expires_at).date().isoformat() if cert.expires_at else '',
        'validity_days': cert.validity_days or (15 if job.service_package == 'cert_15d' else 90),
        'branch': job.booking.branch.name if job.booking_id else '',
        'revoke_reason': (cert.revoke_reason or '') if status == 'revoked' else '',
        'photos': photos,
    }

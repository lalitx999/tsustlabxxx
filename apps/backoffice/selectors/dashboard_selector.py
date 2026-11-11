from django.db.models import Count, Q
from django.utils import timezone

from apps.bookings.models import Booking, CancellationRequest
from apps.customers.models import TopupRequest
from apps.inspections.models import Job
from apps.reports.services.report_service import daily_stats


def dashboard_numbers() -> dict:
    """Aggregates for the Admin Dashboard (a few grouped queries, no per-row loops)."""
    today = timezone.localdate()
    jobs = Job.objects.aggregate(
        total=Count('pk'),
        pending=Count('pk', filter=Q(status='pending')),
        in_progress=Count('pk', filter=Q(status='in_progress')),
        completed=Count('pk', filter=Q(status='completed')),
        cancelled=Count('pk', filter=Q(status='cancelled')),
        authentic=Count('pk', filter=Q(result='authentic')),
        fake=Count('pk', filter=Q(result='fake')),
        inconclusive=Count('pk', filter=Q(result='inconclusive')),
        to_ship=Count('pk', filter=Q(shipping_status__in=('pending_return', 'ready_to_ship'))),
    )
    decided = jobs['authentic'] + jobs['fake'] + jobs['inconclusive']
    total = jobs['total'] or 0
    top_brands = list(Job.objects.values('brand').annotate(n=Count('pk')).order_by('-n')[:5])
    categories = list(Job.objects.values('category').annotate(n=Count('pk')).order_by('-n'))
    for row in top_brands + categories:
        row['percent'] = round(row['n'] * 100 / total) if total else 0
    return {
        **jobs,
        'active_queues': jobs['pending'] + jobs['in_progress'],
        'authentic_ratio': round(jobs['authentic'] * 100 / decided) if decided else 0,
        'top_brands': top_brands,
        'categories': categories,
        'bookings_today': Booking.objects.filter(booking_date=today).exclude(status='cancelled').count(),
        'pending_slips': Booking.objects.filter(payment_status='pending_review').exclude(status='cancelled').count(),
        'pending_cancellations': CancellationRequest.objects.filter(status='pending').count(),
        'pending_topups': TopupRequest.objects.filter(status='pending').count(),
        'stats': daily_stats(today, today),
        'recent_jobs': Job.objects.select_related('customer').order_by('-created_at')[:8],
    }


def shipping_counts() -> dict:
    return Job.objects.exclude(service_package='photo_review').aggregate(
        pending_return=Count('pk', filter=Q(shipping_status='pending_return') | Q(shipping_status='not_applicable', status='completed')),
        ready_to_ship=Count('pk', filter=Q(shipping_status='ready_to_ship')),
        shipped=Count('pk', filter=Q(shipping_status='shipped')),
        delivered=Count('pk', filter=Q(shipping_status='delivered')),
    )

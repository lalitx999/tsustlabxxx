"""Back-office pages that only read data (queue, in progress, completed, QR, membership,
analytics, system, operations). Actions on these pages call the Ajax endpoints in the
other view modules."""
from django.conf import settings
from django.db.models import Count
from django.shortcuts import render
from django.views.decorators.http import require_GET

from apps.backoffice.selectors.dashboard_selector import shipping_counts
from apps.bookings.selectors.booking_selector import pending_cancellations, pending_slip_reviews
from apps.core.decorators import role_required
from apps.core.permissions import ADMIN_ROLES, FRONT_DESK_ROLES, STAFF_ROLES
from apps.customers.selectors import customer_selector
from apps.inspections.models import Job
from apps.inspections.selectors import job_selector


@role_required(*STAFF_ROLES)
@require_GET
def queue(request):
    active = list(job_selector.today_queue().filter(status__in=('pending', 'in_progress')))
    return render(request, 'backoffice/queue.html', {
        'title': 'Queue Management', 'active': active,
        'testing': next((j for j in active if j.status == 'in_progress'), None),
        'waiting': next((j for j in active if j.status == 'pending'), None),
    })


@role_required(*STAFF_ROLES)
@require_GET
def progress(request):
    stage = request.GET.get('stage', 'in_progress')
    stage = stage if stage in ('in_progress', 'pending') else 'in_progress'
    return render(request, 'backoffice/progress.html', {
        'title': 'In Progress', 'stage': stage, 'jobs': job_selector.job_list(status=stage, limit=300)})


@role_required(*STAFF_ROLES)
@require_GET
def completed(request):
    return render(request, 'backoffice/completed.html', {
        'title': 'Completed', 'jobs': job_selector.job_list(status='completed', limit=300)})


@role_required(*STAFF_ROLES)
@require_GET
def qr(request):
    return render(request, 'backoffice/qr.html', {'title': 'QR Verification', 'cert_id': request.GET.get('id', '')[:60]})


@role_required(*STAFF_ROLES)
@require_GET
def membership(request):
    return render(request, 'backoffice/membership.html', {
        'title': 'Membership', 'members': customer_selector.members(limit=300),
        'ledger': customer_selector.recent_credit_entries(limit=50),
        'topups': customer_selector.pending_topups(),
    })


@role_required(*STAFF_ROLES)
@require_GET
def analytics(request):
    rows = list(Job.objects.values('category').annotate(n=Count('pk')).order_by('-n'))
    total = sum(r['n'] for r in rows)
    for r in rows:
        r['percent'] = round(r['n'] * 100 / total) if total else 0
    return render(request, 'backoffice/analytics.html', {'title': 'Analytics', 'rows': rows, 'total': total})


@role_required(*ADMIN_ROLES)
@require_GET
def system(request):
    return render(request, 'backoffice/system.html', {
        'title': 'System Settings', 'site_url': settings.SITE_URL, 'debug': settings.DEBUG,
        'celery_eager': settings.CELERY_TASK_ALWAYS_EAGER,
        'email_ready': bool(settings.EMAIL_HOST), 'line_ready': bool(settings.LINE_CHANNEL_ACCESS_TOKEN),
        'promptpay_ready': bool(settings.PROMPTPAY_RECEIVER_ID),
    })


@role_required(*FRONT_DESK_ROLES)
@require_GET
def operations(request):
    jobs = (Job.objects.select_related('customer', 'booking').exclude(service_package='photo_review')
            .filter(status__in=('completed', 'cancelled')).order_by('-updated_at')[:300])
    return render(request, 'backoffice/operations.html', {
        'title': 'Operations & Delivery', 'jobs': jobs, 'counts': shipping_counts(),
        'cancellations': pending_cancellations(), 'slips': pending_slip_reviews(),
    })

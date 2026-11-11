"""Daily / period revenue and job statistics (same rules as the legacy daily_stats)."""
import datetime

from django.db.models import Count, Q
from django.utils import timezone

from apps.audit.models import WorkflowEvent
from apps.core.exceptions import ServiceError
from apps.core.money import money
from apps.core.services.file_service import request_file
from apps.inspections.models import Job

REVENUE_KEYS = ('revenue_cash', 'revenue_transfer', 'revenue_card', 'revenue_promptpay', 'revenue_member')
METHOD_TO_KEY = {'cash': 'revenue_cash', 'transfer': 'revenue_transfer', 'credit_card': 'revenue_card',
                 'promptpay': 'revenue_promptpay', 'wallet': 'revenue_member', 'credit_balance': 'revenue_member'}
PAID_ACTIONS = ('wallet_payment', 'counter_payment', 'payment_approve')


def parse_period(*, month=None, date_from=None, date_to=None):
    try:
        if month:
            start = datetime.date.fromisoformat(f'{month}-01')
            end = (start.replace(day=28) + datetime.timedelta(days=4)).replace(day=1) - datetime.timedelta(days=1)
        else:
            start = datetime.date.fromisoformat(date_from or timezone.localdate().isoformat())
            end = datetime.date.fromisoformat(date_to or start.isoformat())
        if start > end:
            raise ValueError
    except (ValueError, TypeError):
        raise ServiceError('กรุณาระบุช่วงวันที่ให้ถูกต้อง โดยวันเริ่มต้นไม่เกินวันสิ้นสุด')
    return start, end


def period_label(start, end) -> str:
    return f'{start:%d/%m/%Y}' if start == end else f'{start:%d/%m/%Y} - {end:%d/%m/%Y}'


def daily_stats(start, end) -> dict:
    jobs = Job.objects.filter(created_at__date__range=(start, end))
    stats = jobs.aggregate(
        total_jobs=Count('pk'),
        completed_jobs=Count('pk', filter=Q(status='completed')),
        authentic_jobs=Count('pk', filter=Q(result='authentic')),
        fake_jobs=Count('pk', filter=Q(result='fake')),
        inconclusive_jobs=Count('pk', filter=Q(result='inconclusive')),
    )
    amounts = {key: money(0) for key in REVENUE_KEYS}
    shipping = money(0)
    seen = set()
    events = (WorkflowEvent.objects.filter(created_at__date__range=(start, end), action__in=PAID_ACTIONS)
              .select_related('booking').only('booking__id', 'booking__payment_method', 'booking__price_snapshot'))
    for event in events:
        booking = event.booking
        if booking and booking.pk not in seen and booking.payment_method in METHOD_TO_KEY:
            amounts[METHOD_TO_KEY[booking.payment_method]] += money(booking.price_snapshot.get('total', 0))
            shipping += money(booking.price_snapshot.get('shipping_fee', 0))
            seen.add(booking.pk)
    # Legacy rows without a payment event: count paid jobs by their created day.
    for job in jobs.filter(payment_status='paid', price_snapshot={}).only('booking_id', 'payment_method', 'price'):
        if job.booking_id not in seen and job.payment_method in METHOD_TO_KEY:
            amounts[METHOD_TO_KEY[job.payment_method]] += job.price
    refunds = sum((money(e.detail.get('amount', 0)) for e in WorkflowEvent.objects.filter(
        created_at__date__range=(start, end), action='refund_paid_out').only('detail')), money(0))
    gross = sum(amounts.values(), money(0))
    stats.update({k: float(v) for k, v in amounts.items()})
    stats.update(shipping_received=float(shipping), gross_revenue=float(gross), refunds=float(refunds),
                 total_revenue=float(gross - refunds))
    return stats


def request_report_pdf(start, end, user):
    return request_file(
        kind='daily_report_pdf',
        cache_key=f'report:{start}:{end}:{timezone.now():%Y%m%d%H%M}',
        filename=f'report-{start}-{end}.pdf',
        params={'date_from': start.isoformat(), 'date_to': end.isoformat()}, user=user)

from django.core.cache import cache

from apps.core.permissions import is_admin

from .menu import menu_for


def _alert_count():
    """Items waiting for staff (slips, cancellations, top-ups). Cached briefly to keep pages fast."""
    count = cache.get('bo_alert_count')
    if count is None:
        from apps.bookings.models import Booking, CancellationRequest
        from apps.customers.models import TopupRequest
        count = (Booking.objects.filter(payment_status='pending_review').exclude(status='cancelled').count()
                 + CancellationRequest.objects.filter(status='pending').count()
                 + TopupRequest.objects.filter(status='pending').count())
        cache.set('bo_alert_count', count, 30)
    return count


def backoffice(request):
    """Sidebar menu and the bell counter, only for back-office pages."""
    match = getattr(request, 'resolver_match', None)
    if not match or match.namespace != 'backoffice' or not request.user.is_authenticated:
        return {}
    return {'bo_menu': menu_for(request.user, f'{match.namespace}:{match.url_name}'), 'bo_alerts': _alert_count(),
            'bo_is_admin': is_admin(request.user)}

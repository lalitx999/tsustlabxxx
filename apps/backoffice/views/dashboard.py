from django.shortcuts import render
from django.views.decorators.http import require_GET

from apps.backoffice.selectors.dashboard_selector import dashboard_numbers
from apps.bookings.selectors.booking_selector import bookings_for_day
from apps.core.decorators import role_required
from apps.core.permissions import STAFF_ROLES
from django.utils import timezone


@role_required(*STAFF_ROLES)
@require_GET
def dashboard(request):
    return render(request, 'backoffice/dashboard.html', {
        'title': 'Dashboard',
        'numbers': dashboard_numbers(),
        'today_bookings': bookings_for_day(timezone.localdate())[:20],
    })

"""Customer-facing display (second screen at the counter).

The Walk-in tab sends the current sale to this page with BroadcastChannel inside the same browser,
as on the old site, so nothing extra goes through the server. Staff-only because it runs on the
counter computer next to the Walk-in page.
"""
from django.shortcuts import render
from django.views.decorators.http import require_GET

from apps.core.decorators import role_required
from apps.core.permissions import FRONT_DESK_ROLES


@role_required(*FRONT_DESK_ROLES)
@require_GET
def pos_display(request):
    return render(request, 'backoffice/pos_display.html', {'title': 'Customer Display'})

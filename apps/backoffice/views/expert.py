"""Expert workbench (/authenzs/expert/jobs/): the inspection queue on its own page, as on the old site."""
from django.shortcuts import render
from django.views.decorators.http import require_GET

from apps.core.decorators import ajax_view, role_required
from apps.core.permissions import has_role
from apps.inspections.selectors import job_selector

from .jobs import INSPECTION_ROLES


@role_required(*INSPECTION_ROLES)
@require_GET
def expert_jobs(request):
    return render(request, 'expert/jobs.html', {
        'title': 'Expert Workbench',
        'can_open_backoffice': has_role(request.user, ('admin', 'manager')),
    })


@role_required(*INSPECTION_ROLES)
@require_GET
@ajax_view
def expert_rows(request):
    return [job_selector.serialize_expert_job(job) for job in job_selector.expert_queue()]

"""Queue and finish background-built files (see GeneratedFile)."""
import logging

from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

from apps.core.models import GeneratedFile

logger = logging.getLogger(__name__)

# kind -> dotted path of the builder function: builder(params) -> bytes
BUILDERS = {
    'certificate_pdf': 'apps.inspections.services.certificate_pdf.build_certificate_pdf',
    'daily_report_pdf': 'apps.reports.services.report_pdf.build_daily_report_pdf',
    'return_label_pdf': 'apps.inspections.services.shipping_service.build_return_label',
    'photo_zip': 'apps.inspections.services.photo_service.build_photo_zip',
}


def request_file(*, kind, cache_key, filename, params, user=None, content_type='application/pdf',
                 is_public=False) -> GeneratedFile:
    """Return the existing file for cache_key, or create one and queue its build."""
    from apps.core.tasks import build_generated_file

    item, created = GeneratedFile.objects.get_or_create(
        cache_key=cache_key,
        defaults={'kind': kind, 'filename': filename, 'params': params, 'content_type': content_type,
                  'is_public': is_public, 'requested_by': user if user and user.is_authenticated else None},
    )
    if created or item.status == 'failed':
        if item.status == 'failed':
            GeneratedFile.objects.filter(pk=item.pk).update(status='pending', error='')
            item.status = 'pending'
        # Queue only after the row is committed so the worker can read it.
        transaction.on_commit(lambda: build_generated_file.delay(item.pk))
    return item


def run_builder(file_id: int) -> None:
    """Called by the Celery task: build bytes and store them."""
    from django.utils.module_loading import import_string

    item = GeneratedFile.objects.get(pk=file_id)
    if item.status == 'ready':
        return
    try:
        builder = import_string(BUILDERS[item.kind])
        content = builder(item.params)
    except Exception as exc:  # stored for the UI; full trace goes to the log
        logger.exception('Building %s failed', item)
        GeneratedFile.objects.filter(pk=item.pk).update(status='failed', error=str(exc)[:500],
                                                        finished_at=timezone.now())
        return
    item.file.save(item.filename, ContentFile(content), save=False)
    item.status = 'ready'
    item.finished_at = timezone.now()
    item.save(update_fields=['file', 'status', 'finished_at'])


def status_payload(item: GeneratedFile, download_url: str) -> dict:
    return {
        'id': item.pk,
        'status': item.status,
        'error': item.error if item.status == 'failed' else '',
        'download_url': download_url if item.status == 'ready' else '',
    }

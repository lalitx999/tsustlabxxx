from celery import shared_task

from apps.core.services.file_service import run_builder


@shared_task(acks_late=True)
def build_generated_file(file_id: int) -> None:
    run_builder(file_id)

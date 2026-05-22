from celery import shared_task

from core.logging import get_logger
from documents.services.document_service import DocumentService

logger = get_logger('documents.tasks')


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def parse_document_task(self, doc_id: str) -> None:
    service = DocumentService()
    try:
        service.parse_and_persist(doc_id)
    except Exception as exc:
        logger.error(
            'Parse task failed',
            extra={'doc_id': doc_id, 'event': 'task_failure'},
            exc_info=True,
        )
        raise self.retry(exc=exc) from exc

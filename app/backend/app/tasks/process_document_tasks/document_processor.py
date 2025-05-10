"""
Wrapper for the hybrid document processor.
"""
import logging
from app.celery_worker import celery

# Set up logging
logger = logging.getLogger(__name__)

# Register the new hybrid processor
from app.tasks.process_document_tasks.document_processor_hybrid import process_document_hybrid

@celery.task
def process_document_mvp(document_id: str):
    """
    Using the hybrid document processor for enhanced functionality
    """
    logger.info(f"Using the hybrid document processor for document: {document_id}")
    return process_document_hybrid(document_id)
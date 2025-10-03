from celery import Celery
import os
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("celery_worker")

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery = Celery(
    "ad_rapport_generator",
    broker=redis_url,
    backend=redis_url,
)

# Configure Celery with increased timeouts
celery.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    task_time_limit=1200,  # 20 minutes max runtime (increased from 10)
    task_soft_time_limit=1080,  # 18 minutes warn (increased from 9)
    worker_prefetch_multiplier=1,  # More predictable task execution
    task_acks_late=True,  # Tasks acknowledged after execution
)

# Explicitly import and register task modules to avoid circular imports
# We need to make sure tasks are imported and registered
import app.tasks.process_document_tasks.document_processor_hybrid
# Removed old report_generator_hybrid - using Enhanced AD workflow only
import app.tasks.process_audio_tasks.audio_transcriber

# Import Enhanced AD report tasks
try:
    import app.tasks.generate_report_tasks.ad_report_task
    logger.info("Successfully imported AD report tasks")
except Exception as e:
    logger.warning(f"Could not import AD report tasks: {e}")

# Force reload of tasks
celery.loader.import_default_modules()
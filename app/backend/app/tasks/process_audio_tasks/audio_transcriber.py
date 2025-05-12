"""
Audio transcription module using Whisper.

This module provides functionality to transcribe audio files to text
using OpenAI's Whisper model, with integration into the document processing pipeline.
"""
import os
import uuid
import logging
import tempfile
from typing import Dict, Any, Optional

import whisper
from celery import shared_task

from app.core.config import settings
from app.db.database_service import get_database_service

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize database service
db_service = get_database_service()

# Audio file extensions that are supported
SUPPORTED_EXTENSIONS = {
    "mp3", "wav", "m4a", "ogg", "flac", "aac", "wma"
}


def is_supported_audio_file(filename: str) -> bool:
    """
    Check if the file extension is supported for audio transcription.
    
    Args:
        filename: The name of the file to check
        
    Returns:
        True if the file extension is supported, False otherwise
    """
    if not filename or "." not in filename:
        return False
    
    extension = filename.rsplit(".", 1)[1].lower()
    return extension in SUPPORTED_EXTENSIONS


def prepare_audio_for_transcription(file_path: str) -> str:
    """
    Prepare audio file for transcription, converting if necessary.
    
    Args:
        file_path: Path to the audio file
        
    Returns:
        Path to the prepared audio file
    """
    # For now, just return the original file path
    # In the future, this could include audio preprocessing, format conversion, etc.
    return file_path


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def transcribe_audio(self, document_id: str, model_name: str = "base") -> Dict[str, Any]:
    """
    Transcribe an audio file and update the document with the transcription.
    
    Args:
        document_id: ID of the document containing the audio file
        model_name: The Whisper model to use for transcription
        
    Returns:
        Dictionary with status and document information
    """
    try:
        logger.info(f"Starting transcription for document {document_id}")
        
        # Get document from database
        document = db_service.get_document(document_id)
        if not document:
            logger.error(f"Document not found: {document_id}")
            return {"status": "error", "message": f"Document not found: {document_id}"}
        
        file_path = document.get("file_path")
        if not file_path:
            logger.error(f"No file path in document: {document_id}")
            return {"status": "error", "message": f"No file path in document: {document_id}"}
        
        # Check if file exists
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return {"status": "error", "message": f"File not found: {file_path}"}
        
        # Prepare audio file for transcription
        prepared_file = prepare_audio_for_transcription(file_path)
        
        # Load Whisper model
        logger.info(f"Loading Whisper model: {model_name}")
        model = whisper.load_model(model_name)
        
        # Transcribe audio
        logger.info(f"Transcribing audio: {file_path}")
        result = model.transcribe(prepared_file)
        transcription = result["text"]
        
        # Update document with transcription
        logger.info(f"Updating document {document_id} with transcription")
        db_service.update_document_content(
            document_id=document_id,
            content=transcription
        )
        
        # Update document status
        db_service.update_document_status(document_id, "processed")
        
        # Trigger embedding generation if needed
        # This would be imported and called here based on the document classifier
        # from app.tasks.process_document_tasks.document_processor_hybrid import process_document_async
        # process_document_async.delay(document_id)
        
        logger.info(f"Transcription completed for document {document_id}")
        return {
            "status": "success",
            "document_id": document_id,
            "transcription_length": len(transcription)
        }
        
    except Exception as e:
        logger.error(f"Error transcribing audio: {str(e)}")
        
        # Retry the task if within retry limits
        try:
            self.retry(exc=e)
        except Exception as retry_error:
            logger.error(f"Retry failed: {str(retry_error)}")
            
            # Update document status to error
            db_service.update_document_status(document_id, "error")
            return {"status": "error", "message": str(e)}


@shared_task
def cleanup_temporary_audio(file_path: str) -> Dict[str, Any]:
    """
    Clean up temporary audio files after processing.
    
    Args:
        file_path: Path to the temporary file to clean up
        
    Returns:
        Dictionary with status information
    """
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Removed temporary file: {file_path}")
            return {"status": "success", "message": f"Removed temporary file: {file_path}"}
        else:
            logger.warning(f"Temporary file not found: {file_path}")
            return {"status": "warning", "message": f"Temporary file not found: {file_path}"}
    except Exception as e:
        logger.error(f"Error cleaning up temporary file: {str(e)}")
        return {"status": "error", "message": str(e)}
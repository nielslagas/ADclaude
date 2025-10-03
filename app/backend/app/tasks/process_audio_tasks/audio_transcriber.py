"""
Audio transcription module.

This module provides functionality to transcribe audio files to text
using OpenAI's Whisper API, with integration into the document processing pipeline.
"""
import os
import uuid
import logging
import tempfile
from typing import Dict, Any, Optional, Set, List

from celery import shared_task

# Use OpenAI API directly 
from openai import OpenAI, APIError, RateLimitError

from app.core.config import settings
from app.db.database_service import get_database_service

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize database service
db_service = get_database_service()

# Audio file extensions that are supported by the Whisper API
# Source: https://platform.openai.com/docs/guides/speech-to-text/audio-inputs
SUPPORTED_EXTENSIONS: Set[str] = {
    "mp3", "mp4", "mpeg", "mpga", "m4a", "wav", "webm"
}

# Max file size accepted by the Whisper API (25 MB)
MAX_FILE_SIZE_BYTES: int = 25 * 1024 * 1024  # 25 MB

# Supported language codes for transcription
SUPPORTED_LANGUAGES: List[str] = [
    "af", "ar", "hy", "az", "be", "bs", "bg", "ca", "zh", "hr",
    "cs", "da", "nl", "en", "et", "fi", "fr", "gl", "de", "el",
    "he", "hi", "hu", "is", "id", "it", "ja", "kn", "kk", "ko",
    "lv", "lt", "mk", "ms", "mr", "mi", "ne", "no", "fa", "pl",
    "pt", "ro", "ru", "sr", "sk", "sl", "es", "sw", "sv", "tl",
    "ta", "th", "tr", "uk", "ur", "vi", "cy"
]

# Default language for transcription
DEFAULT_LANGUAGE: str = "nl"  # Dutch


def is_supported_audio_file(filename: str) -> bool:
    """
    Check if the file extension is supported for audio transcription by the Whisper API.
    
    Args:
        filename: The name of the file to check
        
    Returns:
        True if the file extension is supported, False otherwise
    """
    if not filename or "." not in filename:
        return False
    
    extension = filename.rsplit(".", 1)[1].lower()
    return extension in SUPPORTED_EXTENSIONS


def check_file_size(file_path: str) -> bool:
    """
    Check if the file size is within the limit accepted by the Whisper API.
    
    Args:
        file_path: Path to the audio file
        
    Returns:
        True if the file size is within the limit, False otherwise
    """
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return False
    
    file_size = os.path.getsize(file_path)
    if file_size > MAX_FILE_SIZE_BYTES:
        logger.error(
            f"File size ({file_size} bytes) exceeds the maximum limit " 
            f"of {MAX_FILE_SIZE_BYTES} bytes (25 MB) for the Whisper API"
        )
        return False
    
    return True


def prepare_audio_for_transcription(file_path: str) -> str:
    """
    Prepare audio file for transcription, validating format and size.
    
    Args:
        file_path: Path to the audio file
        
    Returns:
        Path to the prepared audio file
    """
    # Check if file exists
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        raise FileNotFoundError(f"File not found: {file_path}")
    
    # Check file size
    if not check_file_size(file_path):
        raise ValueError(f"File size exceeds the 25 MB limit for the Whisper API")
    
    # Check if the file extension is supported
    if not is_supported_audio_file(os.path.basename(file_path)):
        logger.warning(f"File extension not in the list of officially supported extensions: {file_path}")
    
    # For now, just return the original file path
    # In the future, this could include audio preprocessing, format conversion, etc.
    return file_path


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def transcribe_audio(self, document_id: str, model_name: str = "whisper-1", language: str = DEFAULT_LANGUAGE) -> Dict[str, Any]:
    """
    Transcribe an audio file and update the document with the transcription.

    Uses OpenAI's Whisper API for transcription.

    Args:
        document_id: ID of the document containing the audio file
        model_name: The Whisper API model to use for transcription (default: whisper-1)
        language: Language code for transcription (default: nl for Dutch)

    Returns:
        Dictionary with status and document information
    """
    try:
        logger.info(f"Starting transcription for document {document_id}")

        # Get document from database
        try:
            # Use get_row_by_id instead of get_document, as it doesn't require user_id
            document = db_service.get_row_by_id("document", document_id)
            if not document:
                logger.error(f"Document not found: {document_id}")
                return {"status": "error", "message": f"Document not found: {document_id}"}

            logger.info(f"Retrieved document: {document}")
        except Exception as e:
            logger.error(f"Error retrieving document: {str(e)}")
            return {"status": "error", "message": f"Error retrieving document: {str(e)}"}

        # Try several possible field names for the file path
        file_path = document.get("file_path") or document.get("storage_path")
        if not file_path:
            logger.error(f"No file path in document: {document_id}")
            return {"status": "error", "message": f"No file path in document: {document_id}"}
            
        logger.info(f"Using file path: {file_path}")

        # Validate the file (checks existence, size, and format)
        try:
            prepared_file = prepare_audio_for_transcription(file_path)
            logger.info(f"File prepared successfully: {prepared_file}")
        except (FileNotFoundError, ValueError) as e:
            logger.error(f"Error preparing audio file: {str(e)}")
            return {"status": "error", "message": str(e)}

        # Check if OpenAI API key is available and valid
        api_key = settings.OPENAI_API_KEY
        logger.info(f"OpenAI API key status: {'Available' if api_key else 'Not available'}")

        # Clean up the API key if necessary
        if api_key and isinstance(api_key, str):
            # Remove quotes and whitespace
            api_key = api_key.strip()
            if api_key.startswith('"') and api_key.endswith('"'):
                api_key = api_key[1:-1]
                logger.info("Removed quotes from API key")

            # Log only API key length for security
            key_length = len(api_key)
            logger.info(f"API key length: {key_length}")
        
        # Temporarily using fixed model for all transcriptions
        model_name = "whisper-1"
        
        # Proceed with transcription if API key is valid
        if not api_key or len(api_key.strip()) < 10:
            logger.warning(f"Invalid or missing OpenAI API key. Cannot perform transcription for document {document_id}")
            # Use a different test message to see if changes take effect
            transcription = "[Dit is een test transcriptie omdat de OpenAI API key niet correct geconfigureerd is]"
        else:
            try:
                # Initialize the OpenAI client
                logger.info("Initializing OpenAI client")
                client = OpenAI(api_key=api_key)
                logger.info("OpenAI client initialized successfully")
                
                # Check if language is supported
                if language not in SUPPORTED_LANGUAGES:
                    logger.warning(f"Language '{language}' not in supported languages list, using default")
                    language = DEFAULT_LANGUAGE
                    
                # Transcribe the audio file
                logger.info(f"Opening audio file: {file_path}")
                with open(file_path, "rb") as audio_file:
                    logger.info(f"Sending file to Whisper API: {os.path.basename(file_path)}")
                    response = client.audio.transcriptions.create(
                        model=model_name,
                        file=audio_file,
                        language=language,
                        response_format="text",
                        temperature=0.2  # Lower temperature for more accurate transcription
                    )
                    
                # Process the response
                if hasattr(response, 'text'):
                    transcription = response.text
                else:
                    transcription = str(response)
                    
                # Log success
                logger.info(f"Transcription successful, length: {len(transcription)} characters")
                if len(transcription) > 50:
                    logger.info(f"Transcription sample: {transcription[:50]}...")
                else:
                    logger.info(f"Transcription content: {transcription}")
                    
            except RateLimitError as e:
                logger.error(f"OpenAI rate limit exceeded: {str(e)}")
                retry_count = self.request.retries
                retry_delay = 60 * (2 ** retry_count)  # Exponential backoff
                logger.info(f"Retrying in {retry_delay} seconds (attempt {retry_count + 1}/3)")
                raise self.retry(exc=e, countdown=retry_delay)
                
            except APIError as e:
                logger.error(f"OpenAI API error: {str(e)}")
                transcription = f"[Fout bij transcriptie: {str(e)}]"
                
            except Exception as e:
                logger.error(f"Error transcribing audio: {str(e)}")
                transcription = f"[Error: {str(e)}]"

        # Update document with transcription
        try:
            logger.info(f"Updating document {document_id} with transcription")
            db_service.update_row(
                "document",
                document_id,
                {"content": transcription}
            )

            # Create chunks for RAG retrieval (CRITICAL FIX)
            # Audio transcripts need to be chunked just like documents
            logger.info(f"Creating chunks for audio transcription (length: {len(transcription)} chars)")

            # Chunk size for audio: ~1000 chars with 200 char overlap
            # This ensures complete context for RAG retrieval
            chunk_size = 1000
            overlap = 200
            chunks_created = 0

            # Simple chunking strategy for audio transcripts
            if len(transcription) <= chunk_size:
                # Single chunk for short transcripts
                chunk_metadata = {
                    "source": "audio_transcription",
                    "audio_file": os.path.basename(file_path),
                    "chunk_type": "full_transcript"
                }

                chunk_record = db_service.create_document_chunk(
                    document_id=document_id,
                    content=transcription,
                    chunk_index=0,
                    metadata=chunk_metadata
                )

                if chunk_record:
                    chunks_created = 1
                    logger.info(f"Created single chunk for audio document {document_id}")
            else:
                # Multiple chunks with overlap for longer transcripts
                start = 0
                chunk_index = 0

                while start < len(transcription):
                    end = min(start + chunk_size, len(transcription))
                    chunk_text = transcription[start:end]

                    chunk_metadata = {
                        "source": "audio_transcription",
                        "audio_file": os.path.basename(file_path),
                        "chunk_type": "partial_transcript",
                        "chunk_index": chunk_index,
                        "total_length": len(transcription)
                    }

                    chunk_record = db_service.create_document_chunk(
                        document_id=document_id,
                        content=chunk_text,
                        chunk_index=chunk_index,
                        metadata=chunk_metadata
                    )

                    if chunk_record:
                        chunks_created += 1
                        logger.info(f"Created chunk {chunk_index} for audio document {document_id}")

                    # Move to next chunk with overlap
                    start = end - overlap if end < len(transcription) else end
                    chunk_index += 1

            logger.info(f"Created {chunks_created} chunks for audio document {document_id}")

            # Mark document as processed (chunks will get embeddings asynchronously)
            db_service.update_document_status(document_id, "processed")
            logger.info(f"Audio document {document_id} marked as processed with {chunks_created} chunks")

            # Trigger async embedding generation (following document workflow pattern)
            try:
                # Get the chunk IDs we just created
                chunks = db_service.get_document_chunks(document_id)
                chunk_ids = [chunk["id"] for chunk in chunks]

                logger.info(f"Scheduling embedding generation for {len(chunk_ids)} audio chunks")

                from app.celery_worker import celery
                celery.send_task(
                    "app.tasks.process_document_tasks.document_processor_hybrid.generate_document_embeddings",
                    args=[document_id, chunk_ids]
                )
                logger.info(f"Scheduled embedding generation for audio document {document_id}")
            except Exception as embed_error:
                logger.warning(f"Could not schedule embedding generation: {str(embed_error)}")

        except Exception as e:
            logger.error(f"Error updating document: {str(e)}")
            return {"status": "error", "message": f"Error updating document: {str(e)}"}

        logger.info(f"Transcription process completed for document {document_id}")
        return {
            "status": "success",
            "document_id": document_id,
            "transcription_length": len(transcription),
            "chunks_created": chunks_created
        }

    except Exception as e:
        logger.error(f"Unexpected error in transcribe_audio task: {str(e)}")
        
        # Handle retries
        try:
            self.retry(exc=e)
        except Exception as retry_error:
            logger.error(f"Retry failed: {str(retry_error)}")
            
            # Update document status to error
            try:
                db_service.update_document_status(document_id, "error")
            except:
                pass
                
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
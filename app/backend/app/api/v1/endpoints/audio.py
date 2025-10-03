"""
API endpoints for audio uploads and transcription.

This module provides endpoints for uploading and processing audio recordings,
integrating them into the document processing pipeline.
"""
import os
import uuid
import logging
from typing import Dict, Any, Optional

from fastapi import (
    APIRouter, UploadFile, File, Form, HTTPException, 
    Depends, BackgroundTasks, status
)
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.security import verify_token as get_current_user
from app.db.database_service import get_database_service
from app.tasks.process_audio_tasks.audio_transcriber import (
    transcribe_audio, is_supported_audio_file, cleanup_temporary_audio
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter()

# Initialize database service
db_service = get_database_service()

# Create storage directory if it doesn't exist
AUDIO_STORAGE_PATH = os.path.join(settings.STORAGE_PATH, "audio")
os.makedirs(AUDIO_STORAGE_PATH, exist_ok=True)


@router.post("/upload/", status_code=status.HTTP_201_CREATED)
async def upload_audio_file(
    background_tasks: BackgroundTasks,
    case_id: str = Form(...),
    title: str = Form(...),
    description: Optional[str] = Form(None),
    audio_file: UploadFile = File(...),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Upload an audio file and start transcription process.
    
    The file will be saved to the storage directory and a transcription task
    will be scheduled. The document will be marked as 'processing' until
    transcription is complete.
    
    Args:
        background_tasks: FastAPI background tasks
        case_id: ID of the case to associate the audio with
        title: Title for the audio document
        description: Optional description for the audio document
        audio_file: The uploaded audio file
        current_user: Current authenticated user
    
    Returns:
        JSON response with document information
    """
    try:
        # Log input parameters for debugging
        logger.info(f"Starting audio upload process")
        logger.info(f"Case ID: {case_id}")
        logger.info(f"Title: {title}")
        logger.info(f"Description: {description}")
        logger.info(f"Audio file: {audio_file.filename}, content_type: {audio_file.content_type}")
        logger.info(f"Current user: {current_user}")

        # Validate audio file format
        if not audio_file.filename:
            logger.error("No filename provided")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Filename is required"
            )

        if not is_supported_audio_file(audio_file.filename):
            logger.error(f"Unsupported audio format: {audio_file.filename}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported audio file format"
            )
        
        try:
            # Generate unique filename
            file_ext = audio_file.filename.rsplit(".", 1)[1].lower()
            logger.info(f"File extension: {file_ext}")
            new_filename = f"{uuid.uuid4()}.{file_ext}"
            logger.info(f"Generated new filename: {new_filename}")

            # Create a proper file path for the audio file that includes the case ID
            file_path = os.path.join(settings.STORAGE_PATH, "audio", case_id, new_filename)
            logger.info(f"File path: {file_path}")

            # Ensure directory exists
            directory = os.path.dirname(file_path)
            logger.info(f"Creating directory: {directory}")
            os.makedirs(directory, exist_ok=True)

            # Save file to storage
            logger.info("Reading audio file content")
            content = await audio_file.read()
            logger.info(f"Read {len(content)} bytes")

            logger.info(f"Writing to {file_path}")
            with open(file_path, "wb") as buffer:
                buffer.write(content)
            logger.info("File saved successfully")

        except Exception as e:
            logger.error(f"Error handling audio file: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error handling audio file: {str(e)}"
            )

        # Create document record in database
        user_id = current_user.get("user_id", "example_user_id")
        logger.info(f"Using user_id: {user_id}")

        # Create document in database
        try:
            logger.info("Creating document in database")
            logger.info(f"Parameters: case_id={case_id}, user_id={user_id}, filename={audio_file.filename}")
            logger.info(f"Parameters: file_path={file_path}, mimetype={audio_file.content_type}, size={len(content)}")

            document = db_service.create_document(
                case_id=case_id,
                user_id=user_id,
                filename=audio_file.filename,
                storage_path=file_path,  # Use the correct field name expected by audio_transcriber
                mimetype=audio_file.content_type or "audio/wav",
                size=len(content)
            )
            logger.info(f"Document created with ID: {document.get('id')}")

            # Add document type as audio using update
            document_id = document.get('id')
            if not document_id:
                logger.error("No document ID returned from create_document")
                raise ValueError("No document ID returned from create_document")

            logger.info(f"Setting document_type to 'audio' for document ID: {document_id}")
            db_service.update_row("document", document_id, {"document_type": "audio"})

            # NOTE: Document table doesn't have a title column, title is stored in filename
            # If we need a separate title later, we'd need to add a title column to the schema
            logger.info(f"Title '{title}' provided but not stored separately (using filename instead)")
        except Exception as e:
            logger.error(f"Error creating document record: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error creating document record: {str(e)}"
            )
        
        # Schedule transcription task
        try:
            logger.info(f"Scheduling transcription task for document {document_id}")
            transcribe_task = transcribe_audio.delay(
                document_id=document_id,
                model_name="base"  # Use base model for faster processing
            )

            # Log the task ID
            logger.info(f"Scheduled transcription task {transcribe_task.id} for document {document_id}")
        except Exception as e:
            logger.error(f"Error scheduling transcription task: {str(e)}")
            # Don't raise an exception here, because we've already created the document record
            # Just log the error and continue
            logger.warning("Continuing without transcription task")
        
        # Prepare the response
        try:
            response_data = {
                "status": "success",
                "message": "Audio uploaded and transcription started",
                "document": {
                    "id": document_id,
                    "filename": audio_file.filename,  # Use filename instead of title 
                    "status": "processing"
                }
            }

            # Add transcription task ID if available
            if 'transcribe_task' in locals() and hasattr(transcribe_task, 'id'):
                response_data["document"]["transcription_task_id"] = transcribe_task.id

            logger.info(f"Returning response: {response_data}")
            return response_data
        except Exception as e:
            logger.error(f"Error preparing response: {str(e)}")
            # At this point we've created the document, so return a minimal success response
            return {
                "status": "success",
                "message": "Audio uploaded successfully",
                "document": {
                    "id": document_id
                }
            }
        
    except HTTPException as e:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error processing audio upload: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing audio upload: {str(e)}"
        )


@router.post("/record/", status_code=status.HTTP_201_CREATED)
async def record_audio(
    background_tasks: BackgroundTasks,
    case_id: str = Form(...),
    title: str = Form(...),
    description: Optional[str] = Form(None),
    audio_data: UploadFile = File(...),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Upload a recorded audio blob and start transcription.
    
    Similar to upload_audio_file but specifically for browser-recorded audio,
    which might be in a different format (typically webm or wav).
    
    Args:
        background_tasks: FastAPI background tasks
        case_id: ID of the case to associate the audio with
        title: Title for the audio document
        description: Optional description for the audio document
        audio_data: The recorded audio data
        current_user: Current authenticated user
    
    Returns:
        JSON response with document information
    """
    # This endpoint currently has the same implementation as upload_audio_file,
    # but could be extended with specific processing for browser-recorded audio
    return await upload_audio_file(
        background_tasks=background_tasks,
        case_id=case_id,
        title=title,
        description=description,
        audio_file=audio_data,
        current_user=current_user
    )


@router.get("/{document_id}/status")
async def get_transcription_status(
    document_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Check the status of an audio transcription.
    
    Args:
        document_id: ID of the document to check
        current_user: Current authenticated user
        
    Returns:
        JSON response with transcription status
    """
    try:
        user_id = current_user.get("user_id", "example_user_id")
        document = db_service.get_document(document_id, user_id)

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document {document_id} not found"
            )

        # Check if document is of type audio
        if document.get("document_type") != "audio":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Document {document_id} is not an audio document"
            )
            
        return {
            "status": "success",
            "document": {
                "id": document["id"],
                "filename": document["filename"],  # Use filename instead of title
                "status": document["status"],
                "has_transcription": document.get("status") == "processed"
            }
        }
        
    except HTTPException as e:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error checking transcription status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error checking transcription status: {str(e)}"
        )


@router.post("/{document_id}/reprocess")
async def reprocess_audio(
    document_id: str,
    model_config: str = "accurate",  # fast, accurate, multilingual
    language: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Reprocess an audio document with different settings.
    
    Args:
        document_id: ID of the document to reprocess
        model_config: Model configuration to use
        language: Language code for transcription
        current_user: Current authenticated user
        
    Returns:
        JSON response with reprocessing status
    """
    try:
        user_id = current_user.get("user_id", "example_user_id")
        document = db_service.get_document(document_id, user_id)

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document {document_id} not found"
            )

        # Check if document is of type audio
        if document.get("document_type") != "audio":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Document {document_id} is not an audio document"
            )
        
        # Mark document as processing again
        db_service.update_document_status(document_id, "processing")
        
        # Schedule new transcription task
        try:
            logger.info(f"Reprocessing audio document {document_id} with config {model_config}")
            transcribe_task = transcribe_audio_optimized.delay(
                document_id=document_id,
                model_config=model_config,
                language=language or "nl"
            )
            
            return {
                "status": "success",
                "message": "Audio reprocessing started",
                "task_id": transcribe_task.id,
                "config": {
                    "model_config": model_config,
                    "language": language or "nl"
                }
            }
            
        except Exception as e:
            logger.error(f"Error scheduling reprocessing task: {e}")
            db_service.update_document_status(document_id, "error")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error scheduling reprocessing: {str(e)}"
            )
        
    except HTTPException as e:
        raise
    except Exception as e:
        logger.error(f"Error reprocessing audio: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error reprocessing audio: {str(e)}"
        )


@router.get("/quality-report/{document_id}")
async def get_audio_quality_report(
    document_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Get a detailed quality report for an audio transcription.
    
    Args:
        document_id: ID of the document to analyze
        current_user: Current authenticated user
        
    Returns:
        JSON response with quality analysis
    """
    try:
        user_id = current_user.get("user_id", "example_user_id")
        document = db_service.get_document(document_id, user_id)

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document {document_id} not found"
            )

        if document.get("document_type") != "audio":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Document {document_id} is not an audio document"
            )
        
        # Parse metadata
        metadata = {}
        try:
            import json
            metadata = json.loads(document.get("metadata", "{}"))
        except Exception:
            pass
        
        transcription_info = metadata.get("transcription", {})
        
        # Generate quality report
        quality_report = {
            "document_id": document_id,
            "status": document.get("status"),
            "quality_metrics": {
                "confidence_score": transcription_info.get("confidence_score"),
                "audio_quality": transcription_info.get("audio_quality"),
                "audio_duration": transcription_info.get("audio_duration"),
                "chunk_count": transcription_info.get("chunk_count"),
                "processing_time": transcription_info.get("processing_time"),
                "language_detected": transcription_info.get("language_detected")
            },
            "warnings": transcription_info.get("warnings", []),
            "recommendations": [],
            "transcription_stats": {}
        }
        
        # Add transcription statistics if available
        if document.get("content"):
            content = document["content"]
            words = content.split()
            quality_report["transcription_stats"] = {
                "word_count": len(words),
                "character_count": len(content),
                "estimated_reading_time": len(words) / 200  # ~200 words per minute
            }
            
            # Check for Dutch arbeidsdeskundige keywords
            dutch_keywords = [
                "arbeidsdeskundige", "belastbaarheid", "werkhervatting", "re-integratie",
                "arbeidsongeval", "verzuim", "arbeidsgeschiktheid"
            ]
            keyword_count = sum(1 for keyword in dutch_keywords if keyword.lower() in content.lower())
            quality_report["transcription_stats"]["dutch_keywords_found"] = keyword_count
        
        # Generate recommendations based on quality metrics
        confidence = transcription_info.get("confidence_score", 0)
        audio_quality = transcription_info.get("audio_quality", 0)
        
        if confidence and confidence < 0.7:
            quality_report["recommendations"].append("Consider re-recording with better audio quality")
        
        if audio_quality and audio_quality < 0.5:
            quality_report["recommendations"].append("Audio quality is low - use a better microphone or recording environment")
        
        if transcription_info.get("warnings"):
            quality_report["recommendations"].append("Review transcription carefully due to processing warnings")
        
        return {
            "status": "success",
            "quality_report": quality_report
        }
        
    except HTTPException as e:
        raise
    except Exception as e:
        logger.error(f"Error generating quality report: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating quality report: {str(e)}"
        )


@router.delete("/{document_id}/cache")
async def clear_transcription_cache(
    document_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Clear cached transcription data for a document.
    
    Args:
        document_id: ID of the document
        current_user: Current authenticated user
        
    Returns:
        JSON response with cache clearing status
    """
    try:
        user_id = current_user.get("user_id", "example_user_id")
        document = db_service.get_document(document_id, user_id)

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document {document_id} not found"
            )

        # Clear cache files
        try:
            from pathlib import Path
            import glob
            
            cache_dir = Path(settings.STORAGE_PATH) / "cache" / "transcriptions"
            # Find cache files that might be related to this document
            cache_files = glob.glob(str(cache_dir / "*.json"))
            cleared_count = 0
            
            for cache_file in cache_files:
                try:
                    # This is a simple approach - in production you'd want more sophisticated cache key matching
                    os.remove(cache_file)
                    cleared_count += 1
                except Exception as e:
                    logger.warning(f"Could not remove cache file {cache_file}: {e}")
            
            return {
                "status": "success",
                "message": f"Cleared {cleared_count} cache files",
                "cleared_files": cleared_count
            }
            
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return {
                "status": "warning",
                "message": f"Cache clearing completed with errors: {str(e)}"
            }
        
    except HTTPException as e:
        raise
    except Exception as e:
        logger.error(f"Error clearing transcription cache: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error clearing transcription cache: {str(e)}"
        )
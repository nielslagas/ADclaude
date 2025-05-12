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
from app.core.security import get_current_user
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
        # Validate audio file format
        if not audio_file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Filename is required"
            )
            
        if not is_supported_audio_file(audio_file.filename):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported audio file format"
            )
        
        # Generate unique filename
        file_ext = audio_file.filename.rsplit(".", 1)[1].lower()
        new_filename = f"{uuid.uuid4()}.{file_ext}"
        file_path = os.path.join(AUDIO_STORAGE_PATH, new_filename)
        
        # Save file to storage
        with open(file_path, "wb") as buffer:
            content = await audio_file.read()
            buffer.write(content)
        
        # Create document record in database
        document = db_service.create_document(
            case_id=case_id,
            title=title,
            description=description or "",
            filename=audio_file.filename,
            file_path=file_path,
            document_type="audio",
            user_id=current_user.get("id"),
            status="processing"
        )
        
        # Schedule transcription task
        transcribe_task = transcribe_audio.delay(
            document_id=document["id"],
            model_name="base"  # Use base model for faster processing
        )
        
        # Log the task ID
        logger.info(f"Scheduled transcription task {transcribe_task.id} for document {document['id']}")
        
        return {
            "status": "success",
            "message": "Audio uploaded and transcription started",
            "document": {
                "id": document["id"],
                "title": document["title"],
                "status": document["status"],
                "transcription_task_id": transcribe_task.id
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
        document = db_service.get_document(document_id)
        
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
                "title": document["title"],
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
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, Form, File
from typing import List, Optional
from uuid import UUID
import os

from app.core.security import verify_token
from app.models.document import Document, DocumentCreate, DocumentRead
from app.db.database_service import db_service
from app.core.config import settings
# Import the Celery app
from app.celery_worker import celery

router = APIRouter()

@router.post("/upload", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
async def upload_document(
    case_id: UUID = Form(...),
    file: UploadFile = File(...),
    user_info = Depends(verify_token)
):
    """
    Debug info: This endpoint expects a multipart/form-data with:
    - case_id: a UUID of an existing case
    - file: a file upload field containing a .docx or .txt file
    """
    """
    Upload a document for a specific case and start processing
    """
    print("*"*80)
    print("DOCUMENT UPLOAD DEBUG:")
    print(f"Received upload request with case_id: {case_id}")
    print(f"File info: name={file.filename}, content_type={file.content_type}, size=unknown")
    print(f"Headers: {file.headers}")
    print(f"User info: {user_info}")
    print("*"*80)
    
    user_id = user_info["user_id"]
    
    # Check if the case exists and belongs to the user
    try:
        case = db_service.get_case(str(case_id), user_id)
        
        if not case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Case not found"
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Error checking case: {str(e)}"
        )
    
    # Check file size
    if file.size > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds the maximum allowed size of {settings.MAX_UPLOAD_SIZE / (1024 * 1024)}MB"
        )
    
    # Check file type
    print(f"File content_type: {file.content_type}")
    print(f"File filename: {file.filename}")
    
    # For MVP, we'll accept files based on extension in addition to content type
    is_valid_type = (
        file.content_type in ["application/vnd.openxmlformats-officedocument.wordprocessingml.document", 
                             "application/msword", "text/plain"] or
        file.filename.endswith(('.docx', '.doc', '.txt'))
    )
    
    if not is_valid_type:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Only .docx and .txt files are supported. Received content type: {file.content_type}"
        )
    
    try:
        # Read file content
        file_content = await file.read()
        print(f"File read, size: {len(file_content)} bytes")
        
        # Create a storage path for this file
        storage_path = db_service.get_document_storage_path(user_id, str(case_id), file.filename)
        print(f"Storage path: {storage_path}")
        
        # Make sure directory exists
        os.makedirs(os.path.dirname(storage_path), exist_ok=True)
        print(f"Directory created: {os.path.dirname(storage_path)}")
        
        # Save file to local storage
        result = db_service.save_document_file(file_content, storage_path)
        print(f"File save result: {result}")
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save file"
            )
        
        # Create document record in the database
        document = db_service.create_document(
            case_id=str(case_id),
            user_id=user_id,
            filename=file.filename,
            storage_path=storage_path,
            mimetype=file.content_type,
            size=len(file_content)
        )
        
        if not document:
            # Delete the uploaded file if record creation fails
            db_service.delete_document_file(storage_path)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create document record"
            )
            
        # Process the document using the hybrid processor
        document_id = document["id"]
        
        # Start asynchronous processing with Celery
        try:
            # Set document status to processing
            db_service.update_document_status(document_id, "processing")
            
            # Log debugging info
            print(f"About to send Celery task for document {document_id}")
            
            # Send the task to Celery
            task = celery.send_task(
                "app.tasks.process_document_tasks.document_processor_hybrid.process_document_hybrid", 
                args=[document_id]
            )
            
            print(f"Started hybrid document processing for document {document_id}")
            print(f"Task ID: {task.id}")
        except Exception as e:
            print(f"Error starting document processing: {str(e)}")
            # Even if processing fails to start, we keep the document
            
        # Update the document with processing status
        document["status"] = "processing"
        
        return document
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing upload: {str(e)}"
        )

@router.get("/case/{case_id}", response_model=List[DocumentRead])
async def list_case_documents(case_id: UUID, user_info = Depends(verify_token)):
    """
    List all documents for a specific case
    """
    user_id = user_info["user_id"]
    
    try:
        # Check if case exists and belongs to user
        case = db_service.get_case(str(case_id), user_id)
        
        if not case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Case not found"
            )
            
        # Get documents for the case
        documents = db_service.get_documents_for_case(str(case_id))
        
        return documents
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing documents: {str(e)}"
        )

@router.get("/{document_id}", response_model=DocumentRead)
async def get_document(document_id: UUID, user_info = Depends(verify_token)):
    """
    Get a specific document by ID
    """
    user_id = user_info["user_id"]
    
    try:
        document = db_service.get_document(str(document_id), user_id)
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
            
        return document
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving document: {str(e)}"
        )

@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(document_id: UUID, user_info = Depends(verify_token)):
    """
    Delete a document and its storage file
    """
    user_id = user_info["user_id"]
    
    try:
        # Get document to check ownership and get storage path
        document = db_service.get_document(str(document_id), user_id)
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        # Delete from storage
        db_service.delete_document_file(document["storage_path"])
        
        # Delete document record - this will cascade delete document chunks due to foreign key constraint
        success = db_service.delete_row("document", str(document_id))
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete document"
            )
            
        return None
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting document: {str(e)}"
        )
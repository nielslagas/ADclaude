from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from uuid import UUID

from app.core.security import verify_token, require_auth
from app.models.case import Case, CaseCreate, CaseRead, CaseUpdate
from app.db.database_service import db_service

router = APIRouter()

@router.post("/", response_model=CaseRead, status_code=status.HTTP_201_CREATED)
async def create_case(case_data: CaseCreate, user_info = Depends(require_auth)):
    """
    Create a new case
    """
    user_id = user_info["user_id"]
    
    # Create case in database using database service
    try:
        case = db_service.create_case(
            user_id=user_id,
            title=case_data.title,
            description=case_data.description
        )
        
        if not case:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create case"
            )
            
        return case
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating case: {str(e)}"
        )

@router.get("/", response_model=List[CaseRead])
async def list_cases(user_info = Depends(require_auth)):
    """
    List all cases for the current user
    """
    user_id = user_info["user_id"]
    
    try:
        cases = db_service.get_cases_for_user(user_id)
        return cases
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing cases: {str(e)}"
        )

@router.get("/{case_id}", response_model=CaseRead)
async def get_case(case_id: UUID, user_info = Depends(require_auth)):
    """
    Get a specific case by ID
    """
    user_id = user_info["user_id"]
    
    try:
        print(f"Fetching case with ID: {case_id}, User ID: {user_id}")
        case = db_service.get_case(str(case_id), user_id)
        
        if not case:
            print(f"Case not found: {case_id}, User ID: {user_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Case not found"
            )
            
        print(f"Case found: {case}")
        return case
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error retrieving case: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving case: {str(e)}"
        )

@router.patch("/{case_id}", response_model=CaseRead)
async def update_case(case_id: UUID, case_data: CaseUpdate, user_info = Depends(require_auth)):
    """
    Update a case
    """
    user_id = user_info["user_id"]
    
    # First check if case exists and belongs to user
    try:
        existing_case = db_service.get_case(str(case_id), user_id)
        
        if not existing_case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Case not found"
            )
        
        # Prepare update data, only including fields that are provided
        update_data = case_data.model_dump(exclude_unset=True)
        
        # Update the case
        updated_case = db_service.update_case(str(case_id), update_data)
        
        if not updated_case:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update case"
            )
            
        return updated_case
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating case: {str(e)}"
        )

@router.delete("/{case_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_case(case_id: UUID, user_info = Depends(require_auth)):
    """
    Mark a case as deleted (soft delete)
    """
    user_id = user_info["user_id"]
    
    try:
        # Check if case exists and belongs to user
        existing_case = db_service.get_case(str(case_id), user_id)
        
        if not existing_case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Case not found"
            )
        
        # Soft delete the case
        success = db_service.delete_case(str(case_id), user_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete case"
            )
            
        return None
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting case: {str(e)}"
        )

"""
API endpoints for user profiles.
"""
import os
import logging
from typing import List, Optional
from uuid import UUID
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    File,
    UploadFile,
    Form,
    Query
)
from fastapi.responses import FileResponse, Response, JSONResponse
from sqlalchemy import text

from app.core.config import settings
from app.core.security import verify_token
from app.db.database_service import get_database_service
from app.models.user_profile import (
    UserProfile,
    UserProfileCreate,
    UserProfileUpdate,
    UserProfileResponse,
    ProfileLogo,
    ProfileCompletionStatus
)

router = APIRouter()
logger = logging.getLogger(__name__)
db_service = get_database_service()

# Helper function to generate a profile logo URL
def get_logo_url(logo_path: Optional[str]) -> Optional[str]:
    """Generate a URL for a profile logo."""
    if not logo_path:
        return None
    
    return f"/api/v1/profiles/logo/{os.path.basename(logo_path)}"

@router.get("/me", response_model=UserProfileResponse)
async def get_current_user_profile(current_user = Depends(verify_token)):
    """
    Get the profile of the currently authenticated user.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )

    # Get valid user_id
    user_id = current_user.get("user_id")

    # For testing, if this is the mock user, get the real DB user
    if user_id == "example_user_id":
        # Execute a query to get a real user_id
        query = "SELECT id FROM auth.users LIMIT 1;"

        try:
            with db_service.engine.connect() as connection:
                result = connection.execute(text(query))
                user_row = result.fetchone()

                if user_row:
                    user_id = str(user_row[0])
                    logger.info(f"Using real user_id: {user_id} for mock user")
                else:
                    # Create a test user directly in the database
                    logger.info("No users found, creating test user")
                    create_user_query = """
                        INSERT INTO auth.users (email, password)
                        VALUES ('test@example.com', 'password')
                        RETURNING id;
                    """
                    result = connection.execute(text(create_user_query))
                    user_row = result.fetchone()
                    connection.commit()

                    if user_row:
                        user_id = str(user_row[0])
                        logger.info(f"Created test user with id: {user_id}")
                    else:
                        raise HTTPException(
                            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Could not create test user"
                        )
        except Exception as e:
            logger.error(f"Error getting/creating test user: {str(e)}")

    profile = db_service.get_user_profile(user_id)

    if not profile:
        # Try to create a new profile
        profile = db_service.create_user_profile(user_id, {})

        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profile not found and could not be created"
            )

    # Add logo URL if available
    if profile and profile.get("logo_path"):
        profile["logo_url"] = get_logo_url(profile["logo_path"])

    return profile

@router.put("/me", response_model=UserProfileResponse)
async def update_current_user_profile(
    profile_update: UserProfileUpdate,
    current_user = Depends(verify_token)
):
    """
    Update the profile of the currently authenticated user.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Not authenticated"
        )
    
    user_id = current_user.get("user_id")
    
    # Get the existing profile
    profile = db_service.get_user_profile(user_id)
    
    if not profile:
        # Create a new profile
        profile = db_service.create_user_profile(user_id, profile_update.model_dump(exclude_unset=True))
    else:
        # Update the existing profile
        profile = db_service.update_user_profile(
            profile["profile_id"],
            profile_update.model_dump(exclude_unset=True)
        )
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update profile"
        )
    
    # Add logo URL if available
    if profile.get("logo_path"):
        profile["logo_url"] = get_logo_url(profile["logo_path"])
    
    return profile

@router.post("/me/logo", response_model=ProfileLogo)
async def upload_profile_logo(
    file: UploadFile = File(...),
    current_user = Depends(verify_token)
):
    """
    Upload a logo for the user's profile.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Not authenticated"
        )
    
    user_id = current_user.get("user_id")
    
    # Get the profile
    profile = db_service.get_user_profile(user_id)
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )
    
    # Validate file type
    allowed_types = ["image/jpeg", "image/png", "image/gif", "image/svg+xml"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Supported types: {', '.join(allowed_types)}"
        )
    
    # Read the file content
    file_content = await file.read()
    
    # Save the logo
    logo = db_service.save_profile_logo(
        profile_id=profile["profile_id"],
        file_name=file.filename,
        file_content=file_content,
        mime_type=file.content_type,
        size=len(file_content)
    )
    
    if not logo:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save logo"
        )
    
    return logo

@router.get("/logo/{filename}")
async def get_profile_logo(filename: str):
    """
    Get a profile logo by filename.
    """
    logo_path = os.path.join(settings.STORAGE_PATH, "profile_logos", filename)
    
    if not os.path.exists(logo_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Logo not found"
        )
    
    return FileResponse(logo_path)

@router.delete("/me/logo")
async def delete_profile_logo(current_user = Depends(verify_token)):
    """
    Delete the logo for the user's profile.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Not authenticated"
        )
    
    user_id = current_user.get("user_id")
    
    # Get the profile
    profile = db_service.get_user_profile(user_id)
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )
    
    # Check if profile has a logo
    if not profile.get("logo_id"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No logo found for this profile"
        )
    
    # Delete the logo
    success = db_service.delete_profile_logo(profile["logo_id"])
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete logo"
        )
    
    return {"status": "success", "message": "Logo deleted successfully"}

@router.get("/me/completion", response_model=ProfileCompletionStatus)
async def get_profile_completion_status(current_user = Depends(verify_token)):
    """
    Get the completion status of the user's profile.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Not authenticated"
        )
    
    user_id = current_user.get("user_id")
    
    # Get the profile
    profile = db_service.get_user_profile(user_id)
    
    if not profile:
        profile = db_service.create_user_profile(user_id, {})
        
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profile not found and could not be created"
            )
    
    # Define the steps and required fields
    steps = [
        {
            "step_number": 1,
            "title": "Persoonlijke gegevens",
            "fields": ["first_name", "last_name", "job_title"],
            "completed": False
        },
        {
            "step_number": 2,
            "title": "Bedrijfsgegevens",
            "fields": ["company_name", "company_email", "company_phone"],
            "completed": False
        },
        {
            "step_number": 3,
            "title": "Professionele informatie",
            "fields": ["certification", "registration_number", "specializations"],
            "completed": False
        },
        {
            "step_number": 4,
            "title": "Logo en afbeeldingen",
            "fields": ["logo_id"],
            "completed": False
        }
    ]
    
    # Check which steps are completed
    required_fields_missing = []
    
    for step in steps:
        step_completed = True
        for field in step["fields"]:
            if field not in profile or not profile[field]:
                step_completed = False
                required_fields_missing.append(field)
        
        step["completed"] = step_completed
    
    # Calculate completion percentage
    total_required_fields = sum(len(step["fields"]) for step in steps)
    completed_fields = total_required_fields - len(required_fields_missing)
    progress_percentage = int((completed_fields / total_required_fields) * 100) if total_required_fields > 0 else 0
    
    steps_completed = sum(1 for step in steps if step["completed"])
    
    return {
        "progress_percentage": progress_percentage,
        "steps_completed": steps_completed,
        "total_steps": len(steps),
        "steps": steps,
        "required_fields_missing": required_fields_missing
    }
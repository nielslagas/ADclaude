"""
Models for user profiles and logos.
"""
from typing import Optional, List, Union
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict

class ProfileLogoBase(BaseModel):
    """Base model for profile logo attachments."""
    file_name: str
    mime_type: str
    size: int

class ProfileLogoCreate(ProfileLogoBase):
    """Model for creating a new profile logo."""
    profile_id: UUID
    storage_path: str

class ProfileLogo(ProfileLogoBase):
    """Model for retrieved profile logo details."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    profile_id: UUID
    storage_path: str
    created_at: datetime
    updated_at: datetime

class UserProfileBase(BaseModel):
    """Base model with shared user profile fields."""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    display_name: Optional[str] = None
    job_title: Optional[str] = None
    
    # Company information
    company_name: Optional[str] = None
    company_description: Optional[str] = None
    company_address: Optional[str] = None
    company_postal_code: Optional[str] = None
    company_city: Optional[str] = None
    company_country: Optional[str] = None
    company_phone: Optional[str] = None
    company_email: Optional[str] = None
    company_website: Optional[str] = None
    
    # Additional information
    certification: Optional[str] = None
    registration_number: Optional[str] = None
    specializations: Optional[List[str]] = None
    bio: Optional[str] = None

class UserProfileCreate(UserProfileBase):
    """Model for creating a new user profile."""
    user_id: UUID

class UserProfileUpdate(UserProfileBase):
    """Model for updating an existing user profile."""
    pass

class UserProfile(UserProfileBase):
    """Full user profile model with all fields."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime
    logo: Optional[ProfileLogo] = None

class UserProfileResponse(UserProfileBase):
    """User profile model for API response."""
    model_config = ConfigDict(from_attributes=True)

    # Allow either id or profile_id to be used
    id: Optional[UUID] = None
    profile_id: Optional[UUID] = None
    user_id: UUID
    created_at: datetime
    updated_at: datetime
    logo_url: Optional[str] = None
    logo_id: Optional[UUID] = None

# Models for the profile completion wizard
class ProfileWizardStep(BaseModel):
    """A step in the user profile completion wizard."""
    step_number: int
    title: str
    completed: bool
    fields: List[str]
    
class ProfileCompletionStatus(BaseModel):
    """Status of the user profile completion."""
    progress_percentage: int
    steps_completed: int
    total_steps: int
    steps: List[ProfileWizardStep]
    required_fields_missing: List[str]
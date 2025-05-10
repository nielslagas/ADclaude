from sqlmodel import SQLModel, Field, Relationship
from typing import List, Optional
from datetime import datetime
from uuid import UUID, uuid4
from app.models.base import TimeStampedModel

class Case(TimeStampedModel, table=True):
    """
    Case model representing an arbeidsdeskundige case
    """
    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    title: str = Field(index=True)
    description: Optional[str] = Field(default=None)
    user_id: str = Field(index=True)  # Matches user_id from Supabase auth
    status: str = Field(default="active")  # active, archived, deleted
    
    # Relationships - SQLModel will automatically create these
    documents: List["Document"] = Relationship(back_populates="case")
    reports: List["Report"] = Relationship(back_populates="case")


class CaseCreate(SQLModel):
    """
    Schema for creating a new case
    """
    title: str
    description: Optional[str] = None


class CaseRead(SQLModel):
    """
    Schema for reading a case
    """
    id: UUID
    title: str
    description: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None


class CaseUpdate(SQLModel):
    """
    Schema for updating a case
    """
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None

from sqlmodel import SQLModel, Field, Relationship, JSON
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID, uuid4
from sqlalchemy import Column
from app.models.base import TimeStampedModel

class Report(TimeStampedModel, table=True):
    """
    Generated report model
    """
    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    title: str = Field(index=True)
    template_id: str  # Identifier for the template used
    status: str = Field(default="processing")  # processing, generated, failed
    case_id: UUID = Field(foreign_key="case.id", index=True)
    user_id: str = Field(index=True)  # Matches user_id from Supabase auth
    
    # Content stores generated report sections as JSON
    content: Optional[Dict[str, Any]] = Field(default=None, sa_type=JSON)  # JSON field
    
    # Generation metadata - use Column directly to avoid SQLModel field naming issues
    report_metadata: Optional[Dict[str, Any]] = Field(
        default=None, 
        sa_column=Column("metadata", JSON, nullable=True)
    )
    
    # Error message in case of generation failure
    error: Optional[str] = Field(default=None)
    
    # Relationships
    case: "Case" = Relationship(back_populates="reports")


class ReportCreate(SQLModel):
    """
    Schema for creating a new report generation request
    """
    title: str
    template_id: str
    case_id: UUID


class ReportRead(SQLModel):
    """
    Schema for reading a report
    """
    id: UUID
    title: str
    template_id: str
    status: str
    case_id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None
    content: Optional[Dict[str, Any]] = None  # Using 'content' to match the database field name
    metadata: Optional[Dict[str, Any]] = None  # Will map to report_metadata in the Report model
    error: Optional[str] = None


class ReportSectionGenerate(SQLModel):
    """
    Schema for requesting generation of a specific report section
    """
    report_id: UUID
    section_id: str  # Identifier for the section to generate


class ReportTemplate(SQLModel):
    """
    Schema representing a report template
    """
    id: str
    name: str
    description: str
    sections: Dict[str, Any]  # JSON schema of sections

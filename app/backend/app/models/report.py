from sqlmodel import SQLModel, Field, Relationship, JSON
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID, uuid4
from sqlalchemy import Column
from app.models.base import TimeStampedModel

class Report(TimeStampedModel, table=True):
    """
    Generated report model with structured AD report support
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
    
    # New structured report support fields
    generation_method: Optional[str] = Field(default="legacy", index=True)  # legacy, structured, hybrid
    format_version: Optional[str] = Field(default="1.0", index=True)  # Version of the report format
    layout_type: Optional[str] = Field(default="standaard", index=True)  # Layout template type
    export_formats: Optional[Dict[str, Any]] = Field(default=None, sa_type=JSON)  # Available export formats
    quality_metrics: Optional[Dict[str, Any]] = Field(default=None, sa_type=JSON)  # Quality control metrics
    generation_time_ms: Optional[int] = Field(default=None)  # Generation time in milliseconds
    fml_rubrieken_count: Optional[int] = Field(default=0)  # Number of FML rubrieken for quick access
    has_structured_data: Optional[bool] = Field(default=False, index=True)  # Quick check for structured content

    # Relationships
    case: "Case" = Relationship(back_populates="reports")
    comments: List["Comment"] = Relationship(back_populates="report")


class ReportCreate(SQLModel):
    """
    Schema for creating a new report generation request
    """
    title: str
    template_id: str
    case_id: UUID
    layout_type: Optional[str] = "standaard"
    use_structured_output: Optional[bool] = False


class ReportRead(SQLModel):
    """
    Schema for reading a report with structured data support
    """
    id: UUID
    title: str
    template_id: str
    status: str
    case_id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None
    content: Optional[Dict[str, Any]] = None  # Using 'content' to match the database field name
    report_metadata: Optional[Dict[str, Any]] = None  # Maps to metadata field in database
    error: Optional[str] = None
    
    # New structured report fields
    generation_method: Optional[str] = "legacy"
    format_version: Optional[str] = "1.0"
    layout_type: Optional[str] = "standaard"
    export_formats: Optional[Dict[str, Any]] = None
    quality_metrics: Optional[Dict[str, Any]] = None
    generation_time_ms: Optional[int] = None
    fml_rubrieken_count: Optional[int] = 0
    has_structured_data: Optional[bool] = False



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
    layout: str = "standaard"
    sections: Dict[str, Any]  # JSON schema of sections

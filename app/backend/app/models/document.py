from sqlmodel import SQLModel, Field, Relationship, JSON
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID, uuid4
from app.models.base import TimeStampedModel

class Document(TimeStampedModel, table=True):
    """
    Document model for storing uploaded documents
    """
    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    filename: str = Field(index=True)
    storage_path: str  # Path in Supabase storage
    mimetype: str
    size: int  # Size in bytes
    status: str = Field(default="processing")  # processing, processed, failed
    case_id: UUID = Field(foreign_key="case.id", index=True)
    user_id: str = Field(index=True)  # Matches user_id from Supabase auth
    
    # Error message in case of processing failure
    error: Optional[str] = Field(default=None)
    
    # Relationships
    case: "Case" = Relationship(back_populates="documents")
    chunks: List["DocumentChunk"] = Relationship(back_populates="document")


class DocumentCreate(SQLModel):
    """
    Schema for creating a new document record
    """
    filename: str
    storage_path: str
    mimetype: str
    size: int
    case_id: UUID


class DocumentRead(SQLModel):
    """
    Schema for reading a document
    """
    id: UUID
    filename: str
    mimetype: str
    size: int
    status: str
    case_id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None
    error: Optional[str] = None


class DocumentChunk(TimeStampedModel, table=True):
    """
    Document chunk for vector storage
    """
    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    document_id: UUID = Field(foreign_key="document.id", index=True)
    content: str
    chunk_index: int
    chunk_metadata: Optional[Dict[str, Any]] = Field(default=None, sa_type=JSON)  # JSON field for metadata
    embedding_id: Optional[str] = Field(default=None)  # ID in vector database
    
    # Relationships
    document: Document = Relationship(back_populates="chunks")

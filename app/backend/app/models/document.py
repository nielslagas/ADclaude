from sqlmodel import SQLModel, Field, Relationship, JSON
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
from uuid import UUID, uuid4
from app.models.base import TimeStampedModel

class Document(TimeStampedModel, table=True):
    """
    Document model for storing uploaded documents
    """
    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    filename: str = Field(index=True)
    storage_path: str  # Path in storage
    mimetype: str
    size: int  # Size in bytes
    status: str = Field(default="processing")  # processing, processed, enhanced, failed
    document_type: str = Field(default="document", index=True)  # document, audio, image
    case_id: UUID = Field(foreign_key="case.id", index=True)
    user_id: str = Field(index=True)  # Matches user_id from Supabase auth

    # Content field for storing processed text (e.g., transcriptions)
    content: Optional[str] = Field(default=None)

    # Processing metadata
    processing_strategy: Optional[str] = Field(default=None)  # direct_llm, hybrid, full_rag

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
    document_type: str = "document"
    content: Optional[str] = None
    processing_strategy: Optional[str] = None


class DocumentRead(SQLModel):
    """
    Schema for reading a document
    """
    id: UUID
    filename: str
    mimetype: str
    size: int
    status: str
    document_type: str
    case_id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None
    content: Optional[str] = None
    processing_strategy: Optional[str] = None
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

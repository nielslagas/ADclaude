from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime
from uuid import UUID, uuid4
from app.models.base import TimeStampedModel

class Comment(TimeStampedModel, table=True):
    """
    Comment model for report review system
    """
    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    report_id: UUID = Field(foreign_key="report.id", index=True)
    section_id: Optional[str] = Field(default=None, index=True)  # Specific report section, null for general comments
    user_id: str = Field(index=True)  # User who made the comment
    content: str  # Comment text content
    comment_type: str = Field(default="feedback")  # feedback, suggestion, approval, rejection
    status: str = Field(default="open")  # open, addressed, resolved
    is_internal: bool = Field(default=False)  # Internal comments vs client-facing
    
    # Optional parent comment for threaded discussions
    parent_id: Optional[UUID] = Field(default=None, foreign_key="comment.id")
    
    # Relationships
    report: "Report" = Relationship(back_populates="comments")
    parent: Optional["Comment"] = Relationship(back_populates="replies", sa_relationship_kwargs={"remote_side": "Comment.id"})
    replies: List["Comment"] = Relationship(back_populates="parent")

class CommentCreate(SQLModel):
    """
    Schema for creating a new comment
    """
    report_id: UUID
    section_id: Optional[str] = None
    content: str
    comment_type: str = "feedback"
    is_internal: bool = False
    parent_id: Optional[UUID] = None

class CommentUpdate(SQLModel):
    """
    Schema for updating an existing comment
    """
    content: Optional[str] = None
    status: Optional[str] = None
    comment_type: Optional[str] = None

class CommentRead(SQLModel):
    """
    Schema for reading a comment
    """
    id: UUID
    report_id: UUID
    section_id: Optional[str] = None
    user_id: str
    content: str
    comment_type: str
    status: str
    is_internal: bool
    parent_id: Optional[UUID] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    replies: List["CommentRead"] = []

class CommentWithUser(CommentRead):
    """
    Comment with user information included
    """
    user_name: Optional[str] = None
    user_email: Optional[str] = None
from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID, uuid4

class TimeStampedModel(SQLModel):
    """
    Base model with created_at and updated_at fields
    """
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: Optional[datetime] = Field(default=None, nullable=True)

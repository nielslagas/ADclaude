from fastapi import APIRouter, HTTPException, Depends, status
from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.db.postgres import get_db
from app.core.security import require_auth
from app.models.comment import Comment, CommentCreate, CommentRead, CommentUpdate, CommentWithUser
from app.models.report import Report
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/", response_model=CommentRead, status_code=status.HTTP_201_CREATED)
async def create_comment(
    comment: CommentCreate,
    current_user: dict = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Create a new comment for a report section"""
    try:
        # Verify the report exists and user has access
        report_result = db.query(Report).filter(Report.id == comment.report_id).first()
        
        if not report_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Report not found"
            )
        
        # Check if user has access to this report (same user or admin)
        if report_result.user_id != current_user["user_id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to comment on this report"
            )
        
        # If replying to a comment, verify parent exists
        if comment.parent_id:
            parent_result = db.query(Comment).filter(Comment.id == comment.parent_id).first()
            if not parent_result:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Parent comment not found"
                )
        
        # Create new comment
        db_comment = Comment(
            report_id=comment.report_id,
            section_id=comment.section_id,
            user_id=current_user["user_id"],
            content=comment.content,
            comment_type=comment.comment_type,
            is_internal=comment.is_internal,
            parent_id=comment.parent_id
        )
        
        db.add(db_comment)
        db.commit()
        db.refresh(db_comment)
        
        logger.info(f"Created comment {db_comment.id} for report {comment.report_id}")
        return db_comment
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating comment: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create comment"
        )

@router.get("/report/{report_id}", response_model=List[CommentRead])
async def get_report_comments(
    report_id: UUID,
    section_id: Optional[str] = None,
    include_internal: bool = False,
    current_user: dict = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Get all comments for a report, optionally filtered by section"""
    try:
        # Verify the report exists and user has access
        report_result = db.query(Report).filter(Report.id == report_id).first()
        
        if not report_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Report not found"
            )
        
        # Check if user has access to this report
        if report_result.user_id != current_user["user_id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view comments for this report"
            )
        
        # Build query for comments
        query = db.query(Comment).filter(Comment.report_id == report_id)
        
        if section_id:
            query = query.filter(Comment.section_id == section_id)
        
        if not include_internal:
            query = query.filter(Comment.is_internal == False)
        
        # Only get top-level comments (no parent), replies will be included via relationship
        query = query.filter(Comment.parent_id.is_(None))
        
        # Order by creation date
        query = query.order_by(Comment.created_at.desc())
        
        comments = query.all()
        
        logger.info(f"Retrieved {len(comments)} comments for report {report_id}")
        return comments
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving comments for report {report_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve comments"
        )

@router.put("/{comment_id}", response_model=CommentRead)
async def update_comment(
    comment_id: UUID,
    comment_update: CommentUpdate,
    current_user: dict = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Update an existing comment"""
    try:
        # Get the existing comment
        db_comment = db.query(Comment).filter(Comment.id == comment_id).first()
        
        if not db_comment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Comment not found"
            )
        
        # Check if user owns this comment
        if db_comment.user_id != current_user["user_id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this comment"
            )
        
        # Update the comment fields
        update_data = comment_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_comment, field, value)
        
        db.add(db_comment)
        db.commit()
        db.refresh(db_comment)
        
        logger.info(f"Updated comment {comment_id}")
        return db_comment
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating comment {comment_id}: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update comment"
        )

@router.delete("/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
    comment_id: UUID,
    current_user: dict = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Delete a comment (soft delete by marking as resolved)"""
    try:
        # Get the existing comment
        db_comment = db.query(Comment).filter(Comment.id == comment_id).first()
        
        if not db_comment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Comment not found"
            )
        
        # Check if user owns this comment
        if db_comment.user_id != current_user["user_id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this comment"
            )
        
        # Soft delete: mark as resolved instead of actually deleting
        db_comment.status = "resolved"
        db.add(db_comment)
        db.commit()
        
        logger.info(f"Soft deleted comment {comment_id}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting comment {comment_id}: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete comment"
        )

@router.post("/{comment_id}/resolve", response_model=CommentRead)
async def resolve_comment(
    comment_id: UUID,
    current_user: dict = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Mark a comment as resolved"""
    try:
        # Get the existing comment
        db_comment = db.query(Comment).filter(Comment.id == comment_id).first()
        
        if not db_comment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Comment not found"
            )
        
        # Check if user has access to the report
        report_result = db.query(Report).filter(Report.id == db_comment.report_id).first()
        
        if not report_result or report_result.user_id != current_user["user_id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to resolve this comment"
            )
        
        # Mark as resolved
        db_comment.status = "resolved"
        db.add(db_comment)
        db.commit()
        db.refresh(db_comment)
        
        logger.info(f"Resolved comment {comment_id}")
        return db_comment
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resolving comment {comment_id}: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to resolve comment"
        )
from fastapi import APIRouter, Depends, HTTPException, status
from app.core.security import verify_token

router = APIRouter()

# Since Supabase handles authentication, the backend mainly validates tokens
# and retrieves user information for authorization purposes

@router.get("/me", summary="Get current user info")
async def get_current_user(user_info = Depends(verify_token)):
    """
    Get current authenticated user information
    """
    return user_info

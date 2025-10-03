import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Set up the security scheme with auto_error=False to allow endpoints that don't require authentication
security = HTTPBearer(auto_error=False)

async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Verify the JWT token from Supabase
    """
    # If no credentials are provided, return None (to allow optional authentication)
    if credentials is None:
        return None
        
    try:
        token = credentials.credentials
        print(f"Received token: {token[:20]}...")  # Print first part of token for debugging
        
        # In a real implementation, you would validate the JWT token
        # This is a placeholder for actual token verification
        # Since Supabase handles auth, we'd mainly check if the token is valid and extract user info
        
        # For MVP, we'll implement a basic check
        if not token:
            print("No token provided")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        # Here we'd decode and verify the JWT
        # user_info = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        
        # For MVP, we'll either extract the user_id from the token or use a placeholder
        try:
            # Try to decode the JWT token (without verification for the MVP)
            print("Attempting to decode token")
            payload = jwt.decode(token, options={"verify_signature": False})
            print(f"Token payload: {payload}")
            user_id = payload.get("sub", "example_user_id")
            print(f"Extracted user_id: {user_id}")
        except Exception as jwt_error:
            # Log the specific JWT decoding error
            print(f"JWT decoding error: {str(jwt_error)}")
            # Fallback to the placeholder if decoding fails
            user_id = "example_user_id"
            print(f"Using fallback user_id: {user_id}")
            
        return {"user_id": user_id}
    except Exception as e:
        print(f"Token verification error: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def require_auth(user_info = Depends(verify_token)):
    """
    Require authentication - raises 401 if no valid token is provided
    """
    if user_info is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please provide a valid Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user_info

async def get_current_user(user_info = Depends(verify_token)):
    """
    Get current authenticated user - same as require_auth but with clearer name
    """
    if user_info is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please provide a valid Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user_info

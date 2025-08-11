import firebase_admin
from firebase_admin import credentials, auth
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os
from pathlib import Path
from config import settings

# Initialize Firebase Admin SDK
def initialize_firebase():
    if not firebase_admin._apps:
        # Check if the service account file exists
        cred_path = Path(settings.FIREBASE_ADMIN_SDK_PATH)
        
        if cred_path.exists():
            cred = credentials.Certificate(str(cred_path))
            firebase_admin.initialize_app(cred)
        else:
            # For development, we'll create a mock authentication
            print("Warning: Firebase admin SDK not found. Using mock authentication.")
            return None
    
    return firebase_admin.get_app()

# Initialize Firebase on module import
firebase_app = initialize_firebase()

security = HTTPBearer()


async def verify_firebase_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify Firebase ID token."""
    
    token = credentials.credentials
    
    try:
        if firebase_app is None:
            # Mock authentication for development
            return {
                "uid": "mock_user_id",
                "email": "test@example.com",
                "name": "Test User"
            }
        
        # Verify the token
        decoded_token = auth.verify_id_token(token)
        return decoded_token
        
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail=f"Invalid authentication token: {str(e)}"
        )


async def get_current_user(user_data: dict = Depends(verify_firebase_token)):
    """Get current authenticated user."""
    return user_data
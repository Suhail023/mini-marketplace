"""User management routes."""

from pathlib import Path
import sys

# Add shared modules to path
shared_path = Path(__file__).parent.parent.parent.parent.parent / "shared"
sys.path.insert(0, str(shared_path))


from fastapi import APIRouter
from pydantic import BaseModel

from common.responses import ApiResponse

router = APIRouter()


class UserProfile(BaseModel):
    """User profile model."""

    id: str
    email: str
    first_name: str
    last_name: str
    phone: str | None = None


class UpdateProfileRequest(BaseModel):
    """Update profile request."""

    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None


@router.get("/me", response_model=ApiResponse)
async def get_current_user():
    """Get current user profile."""
    # TODO: Implement actual user retrieval
    return ApiResponse(
        success=True,
        data={"id": "123", "email": "user@example.com", "first_name": "John", "last_name": "Doe"},
        message="User profile retrieved (placeholder)",
    )


@router.put("/me", response_model=ApiResponse)
async def update_profile(request: UpdateProfileRequest):
    """Update user profile."""
    # TODO: Implement actual profile update
    return ApiResponse(
        success=True, data={"updated": True}, message="Profile updated (placeholder)"
    )


@router.delete("/me", response_model=ApiResponse)
async def delete_account():
    """Delete user account."""
    # TODO: Implement actual account deletion
    return ApiResponse(success=True, message="Account deleted (placeholder)")

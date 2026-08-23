"""User management routes."""

import sys
from pathlib import Path

# Add shared modules to path
shared_path = Path(__file__).parent.parent.parent.parent.parent / "shared"
sys.path.insert(0, str(shared_path))

from fastapi import APIRouter, HTTPException, status
from common.responses import ApiResponse
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


class UserProfile(BaseModel):
    """User profile model."""
    id: str
    email: str
    first_name: str
    last_name: str
    phone: Optional[str] = None


class UpdateProfileRequest(BaseModel):
    """Update profile request."""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None


@router.get("/me", response_model=ApiResponse)
async def get_current_user():
    """Get current user profile."""
    # TODO: Implement actual user retrieval
    return ApiResponse(
        success=True,
        data={
            "id": "123",
            "email": "user@example.com",
            "first_name": "John",
            "last_name": "Doe"
        },
        message="User profile retrieved (placeholder)"
    )


@router.put("/me", response_model=ApiResponse)
async def update_profile(request: UpdateProfileRequest):
    """Update user profile."""
    # TODO: Implement actual profile update
    return ApiResponse(
        success=True,
        data={"updated": True},
        message="Profile updated (placeholder)"
    )


@router.delete("/me", response_model=ApiResponse)
async def delete_account():
    """Delete user account."""
    # TODO: Implement actual account deletion
    return ApiResponse(
        success=True,
        message="Account deleted (placeholder)"
    )

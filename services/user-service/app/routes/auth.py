"""Authentication routes for User Service."""

from pathlib import Path
import sys

# Add shared modules to path
shared_path = Path(__file__).parent.parent.parent.parent.parent / "shared"
sys.path.insert(0, str(shared_path))

from fastapi import APIRouter
from pydantic import BaseModel, EmailStr

from common.responses import ApiResponse

router = APIRouter()


class LoginRequest(BaseModel):
    """Login request model."""

    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    """Registration request model."""

    email: EmailStr
    password: str
    first_name: str
    last_name: str


@router.post("/login", response_model=ApiResponse)
async def login(request: LoginRequest):
    """User login endpoint."""
    # TODO: Implement actual authentication logic
    return ApiResponse(
        success=True,
        data={"token": "placeholder_token", "user_id": "123"},
        message="Login successful (placeholder)",
    )


@router.post("/register", response_model=ApiResponse)
async def register(request: RegisterRequest):
    """User registration endpoint."""
    # TODO: Implement actual registration logic
    return ApiResponse(
        success=True,
        data={"user_id": "123", "email": request.email},
        message="Registration successful (placeholder)",
    )


@router.post("/logout", response_model=ApiResponse)
async def logout():
    """User logout endpoint."""
    # TODO: Implement actual logout logic
    return ApiResponse(success=True, message="Logout successful (placeholder)")

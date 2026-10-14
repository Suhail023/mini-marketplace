"""Auth request/response contracts."""

from typing import TYPE_CHECKING

from pydantic import BaseModel, EmailStr

if TYPE_CHECKING:
    from app.models.user import User


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str


class UserResponse(BaseModel):
    id: str
    email: str
    first_name: str
    last_name: str
    is_active: bool
    is_verified: bool

    @classmethod
    def from_user_model(cls, user: "User") -> "UserResponse":
        return cls(
            id=user.id,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            is_active=user.is_active,
            is_verified=user.is_verified,
        )


class UpdateProfileRequest(BaseModel):
    first_name: str | None = None
    last_name: str | None = None


class MessageResponse(BaseModel):
    message: str

"""User management routes."""

from fastapi import APIRouter, Depends

from app.contracts.auth import UpdateProfileRequest, UserResponse
from app.dependencies import get_current_user, get_user_service
from app.models.user import User
from app.services.user_service import UserService

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(current_user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse.from_user_model(current_user)


@router.put("/me", response_model=UserResponse)
async def update_profile(
    request: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    service: UserService = Depends(get_user_service),
) -> UserResponse:
    return await service.update_profile(current_user, request)


@router.delete("/me", status_code=204)
async def delete_account(
    current_user: User = Depends(get_current_user),
    service: UserService = Depends(get_user_service),
) -> None:
    await service.deactivate(current_user)

"""Profile management for the authenticated user."""

from app.contracts.auth import UpdateProfileRequest, UserResponse
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.utils.errors import ForbiddenError, UnauthorizedError


class UserService:
    def __init__(self, user_repository: UserRepository) -> None:
        self.user_repository = user_repository

    async def get_active_user(self, user_id: str) -> User:
        user = await self.user_repository.get_by_id(user_id)
        if user is None:
            raise UnauthorizedError("User not found")
        if not user.is_active:
            raise ForbiddenError("User account is disabled")
        return user

    async def update_profile(self, user: User, request: UpdateProfileRequest) -> UserResponse:
        fields = request.model_dump(exclude_none=True)
        if fields:
            user = await self.user_repository.update(user, fields)
        return UserResponse.from_user_model(user)

    async def deactivate(self, user: User) -> None:
        await self.user_repository.update(user, {"is_active": False})

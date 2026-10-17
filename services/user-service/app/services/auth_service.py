"""Registration and login."""

from app.contracts.auth import LoginRequest, RegisterRequest, TokenResponse
from app.models.user import User
from app.repositories.user_repository import EMAIL_TAKEN_MESSAGE, UserRepository
from app.utils.errors import ConflictError, ForbiddenError, UnauthorizedError
from app.utils.jwt import build_token_claims, create_access_token
from app.utils.password import hash_password, verify_password


def _issue_token(user: User) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(data=build_token_claims(user.id, user.email)),
        user_id=user.id,
        email=user.email,
    )


class AuthService:
    def __init__(self, user_repository: UserRepository) -> None:
        self.user_repository = user_repository

    async def register(self, request: RegisterRequest) -> TokenResponse:
        if await self.user_repository.get_by_email(request.email):
            raise ConflictError(EMAIL_TAKEN_MESSAGE, "email")

        user = await self.user_repository.create(
            {
                "email": request.email,
                "hashed_password": hash_password(request.password),
                "first_name": request.first_name,
                "last_name": request.last_name,
            }
        )
        return _issue_token(user)

    async def login(self, request: LoginRequest) -> TokenResponse:
        user = await self.user_repository.get_by_email(request.email)
        if user is None or not verify_password(request.password, user.hashed_password):
            raise UnauthorizedError("Invalid email or password")
        if not user.is_active:
            raise ForbiddenError("User account is disabled")
        return _issue_token(user)

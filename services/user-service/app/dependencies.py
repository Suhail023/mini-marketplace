"""Composition root: wires repositories into services, and resolves the current user."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService
from app.services.user_service import UserService
from common.auth import Principal, get_current_principal


def get_user_repository(session: AsyncSession = Depends(get_db)) -> UserRepository:
    return UserRepository(session)


def get_auth_service(repository: UserRepository = Depends(get_user_repository)) -> AuthService:
    return AuthService(repository)


def get_user_service(repository: UserRepository = Depends(get_user_repository)) -> UserService:
    return UserService(repository)


async def get_current_user(
    principal: Principal = Depends(get_current_principal),
    service: UserService = Depends(get_user_service),
) -> User:
    return await service.get_active_user(principal.user_id)

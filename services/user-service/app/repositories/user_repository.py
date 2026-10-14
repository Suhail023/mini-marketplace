"""User repository."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.utils.errors import ConflictError

EMAIL_TAKEN_MESSAGE = "A user with this email already exists"


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, user_id: str) -> User | None:
        return await self.session.get(User, user_id)

    async def get_by_email(self, email: str) -> User | None:
        result = await self.session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def create(self, fields: dict[str, Any]) -> User:
        user = User(**fields)
        self.session.add(user)
        try:
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            raise ConflictError(EMAIL_TAKEN_MESSAGE, "email")
        await self.session.refresh(user)
        return user

    async def update(self, user: User, fields: dict[str, Any]) -> User:
        for key, value in fields.items():
            setattr(user, key, value)
        await self.session.commit()
        await self.session.refresh(user)
        return user

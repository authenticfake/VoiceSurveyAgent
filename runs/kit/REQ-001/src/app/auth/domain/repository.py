from __future__ import annotations

from typing import Protocol
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.domain.models import OidcProfile, UserORM, UserProfile


class UserRepository(Protocol):
    async def upsert_from_oidc(self, profile: OidcProfile) -> UserProfile: ...

    async def get_by_id(self, user_id: UUID) -> UserProfile | None: ...

    async def get_by_oidc_sub(self, sub: str) -> UserProfile | None: ...


class SqlAlchemyUserRepository(UserRepository):
    """SQLAlchemy-backed repository for persisting OIDC users."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def upsert_from_oidc(self, profile: OidcProfile) -> UserProfile:
        stmt = select(UserORM).where(UserORM.oidc_sub == profile.sub)
        result = await self._session.execute(stmt)
        user = result.scalar_one_or_none()
        if user:
            user.apply_profile(profile)
        else:
            user = UserORM(
                oidc_sub=profile.sub,
                email=profile.email,
                name=profile.name,
                role=profile.role,
            )
            self._session.add(user)
        await self._session.commit()
        await self._session.refresh(user)
        return user.to_domain()

    async def get_by_id(self, user_id: UUID) -> UserProfile | None:
        stmt = select(UserORM).where(UserORM.id == user_id)
        result = await self._session.execute(stmt)
        user = result.scalar_one_or_none()
        return user.to_domain() if user else None

    async def get_by_oidc_sub(self, sub: str) -> UserProfile | None:
        stmt = select(UserORM).where(UserORM.oidc_sub == sub)
        result = await self._session.execute(stmt)
        user = result.scalar_one_or_none()
        return user.to_domain() if user else None
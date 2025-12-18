"""
User repository for database operations.

REQ-002: OIDC authentication integration
"""

from typing import Protocol
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User


class UserRepositoryProtocol(Protocol):
    """Protocol for user repository operations."""

    async def get_by_id(self, user_id: UUID) -> User | None: ...
    async def get_by_oidc_sub(self, oidc_sub: str) -> User | None: ...
    async def get_by_email(self, email: str) -> User | None: ...
    async def create(self, user: User) -> User: ...
    async def update(self, user: User) -> User: ...
    async def upsert_from_oidc(
        self,
        oidc_sub: str,
        email: str,
        name: str,
    ) -> User: ...


class UserRepository:
    """Repository for user database operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session.

        Args:
            session: Async database session.
        """
        self._session = session

    async def get_by_id(self, user_id: UUID) -> User | None:
        """Get user by ID.

        Args:
            user_id: User UUID.

        Returns:
            User if found, None otherwise.
        """
        result = await self._session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_oidc_sub(self, oidc_sub: str) -> User | None:
        """Get user by OIDC subject identifier.

        Args:
            oidc_sub: OIDC subject identifier.

        Returns:
            User if found, None otherwise.
        """
        result = await self._session.execute(
            select(User).where(User.oidc_sub == oidc_sub)
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        """Get user by email.

        Args:
            email: User email address.

        Returns:
            User if found, None otherwise.
        """
        result = await self._session.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def create(self, user: User) -> User:
        """Create a new user.

        Args:
            user: User model instance.

        Returns:
            Created user with generated ID.
        """
        self._session.add(user)
        await self._session.flush()
        await self._session.refresh(user)
        return user

    async def update(self, user: User) -> User:
        """Update an existing user.

        Args:
            user: User model instance with updates.

        Returns:
            Updated user.
        """
        await self._session.flush()
        await self._session.refresh(user)
        return user

    async def upsert_from_oidc(
        self,
        oidc_sub: str,
        email: str,
        name: str,
    ) -> User:
        """Create or update user from OIDC claims.

        Creates a new user if not found by oidc_sub, otherwise updates
        the existing user's email and name.

        Args:
            oidc_sub: OIDC subject identifier.
            email: User email from OIDC claims.
            name: User name from OIDC claims.

        Returns:
            Created or updated user.
        """
        user = await self.get_by_oidc_sub(oidc_sub)

        if user is None:
            # Create new user with default viewer role
            user = User(
                oidc_sub=oidc_sub,
                email=email,
                name=name,
                role="viewer",
            )
            return await self.create(user)

        # Update existing user
        user.email = email
        user.name = name
        return await self.update(user)
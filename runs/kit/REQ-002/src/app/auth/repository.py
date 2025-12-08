"""Repository for user data access."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User, UserRole
from app.auth.schemas import UserCreate, UserUpdate
from app.shared.logging import get_logger

logger = get_logger(__name__)

class UserRepository:
    """Repository for user CRUD operations."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, user_id: UUID) -> User | None:
        """Get user by ID."""
        result = await self._session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_oidc_sub(self, oidc_sub: str) -> User | None:
        """Get user by OIDC subject identifier."""
        result = await self._session.execute(
            select(User).where(User.oidc_sub == oidc_sub)
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        """Get user by email."""
        result = await self._session.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def create(self, user_data: UserCreate) -> User:
        """Create a new user."""
        user = User(
            oidc_sub=user_data.oidc_sub,
            email=user_data.email,
            name=user_data.name,
            role=user_data.role,
        )
        self._session.add(user)
        await self._session.flush()
        await self._session.refresh(user)
        logger.info(f"Created user: {user.id}")
        return user

    async def update(self, user: User, user_data: UserUpdate) -> User:
        """Update an existing user."""
        if user_data.name is not None:
            user.name = user_data.name
        if user_data.role is not None:
            user.role = user_data.role

        await self._session.flush()
        await self._session.refresh(user)
        logger.info(f"Updated user: {user.id}")
        return user

    async def upsert_from_oidc(
        self,
        oidc_sub: str,
        email: str,
        name: str,
    ) -> User:
        """Create or update user from OIDC claims."""
        user = await self.get_by_oidc_sub(oidc_sub)

        if user is None:
            # Create new user
            user_data = UserCreate(
                oidc_sub=oidc_sub,
                email=email,
                name=name,
                role=UserRole.VIEWER,  # Default role for new users
            )
            return await self.create(user_data)
        else:
            # Update existing user if email or name changed
            if user.email != email or user.name != name:
                user_data = UserUpdate(
                    name=name if user.name != name else None,
                )
                # Update email directly if changed
                if user.email != email:
                    user.email = email
                return await self.update(user, user_data)
            return user
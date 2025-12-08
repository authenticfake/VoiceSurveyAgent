"""User repository for persistence operations."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

from app.auth.domain import User, UserCreate, UserRole, UserUpdate


class UserRepository(ABC):
    """Abstract user repository interface."""

    @abstractmethod
    async def get_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        """Get user by ID."""
        ...

    @abstractmethod
    async def get_by_oidc_sub(self, oidc_sub: str) -> Optional[User]:
        """Get user by OIDC subject identifier."""
        ...

    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        ...

    @abstractmethod
    async def create(self, user_data: UserCreate) -> User:
        """Create a new user."""
        ...

    @abstractmethod
    async def update(self, user_id: uuid.UUID, user_data: UserUpdate) -> Optional[User]:
        """Update an existing user."""
        ...

    @abstractmethod
    async def upsert_from_oidc(
        self, oidc_sub: str, email: str, name: str, default_role: Optional[UserRole] = None
    ) -> User:
        """Create or update user from OIDC claims."""
        ...


class InMemoryUserRepository(UserRepository):
    """In-memory user repository for testing."""

    def __init__(self) -> None:
        """Initialize empty repository."""
        self._users: dict[uuid.UUID, User] = {}
        self._by_sub: dict[str, uuid.UUID] = {}
        self._by_email: dict[str, uuid.UUID] = {}

    async def get_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        """Get user by ID."""
        return self._users.get(user_id)

    async def get_by_oidc_sub(self, oidc_sub: str) -> Optional[User]:
        """Get user by OIDC subject identifier."""
        user_id = self._by_sub.get(oidc_sub)
        if user_id:
            return self._users.get(user_id)
        return None

    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        user_id = self._by_email.get(email.lower())
        if user_id:
            return self._users.get(user_id)
        return None

    async def create(self, user_data: UserCreate) -> User:
        """Create a new user."""
        user = User(
            id=uuid.uuid4(),
            oidc_sub=user_data.oidc_sub,
            email=user_data.email,
            name=user_data.name,
            role=user_data.role or UserRole.VIEWER,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        self._users[user.id] = user
        self._by_sub[user.oidc_sub] = user.id
        self._by_email[user.email.lower()] = user.id
        return user

    async def update(self, user_id: uuid.UUID, user_data: UserUpdate) -> Optional[User]:
        """Update an existing user."""
        user = self._users.get(user_id)
        if not user:
            return None

        update_dict = user_data.model_dump(exclude_unset=True)
        if update_dict:
            # Handle email index update
            if "email" in update_dict and update_dict["email"]:
                old_email = user.email.lower()
                if old_email in self._by_email:
                    del self._by_email[old_email]
                self._by_email[update_dict["email"].lower()] = user_id

            updated_user = user.model_copy(
                update={**update_dict, "updated_at": datetime.utcnow()}
            )
            self._users[user_id] = updated_user
            return updated_user
        return user

    async def upsert_from_oidc(
        self, oidc_sub: str, email: str, name: str, default_role: Optional[UserRole] = None
    ) -> User:
        """Create or update user from OIDC claims."""
        existing = await self.get_by_oidc_sub(oidc_sub)
        if existing:
            # Update email and name if changed
            return await self.update(
                existing.id, UserUpdate(email=email, name=name)
            ) or existing

        # Create new user
        return await self.create(
            UserCreate(
                oidc_sub=oidc_sub,
                email=email,
                name=name,
                role=default_role,
            )
        )

    def clear(self) -> None:
        """Clear all users (for testing)."""
        self._users.clear()
        self._by_sub.clear()
        self._by_email.clear()
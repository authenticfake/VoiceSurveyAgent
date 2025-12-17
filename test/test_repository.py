"""
Tests for user repository.

REQ-002: OIDC authentication integration
"""

from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.auth.repository import UserRepository


class TestUserRepository:
    """Tests for UserRepository."""

    @pytest_asyncio.fixture
    async def repository(self, db_session: AsyncSession) -> UserRepository:
        """Create repository instance."""
        return UserRepository(session=db_session)

    @pytest.mark.asyncio
    async def test_create_user(
        self,
        repository: UserRepository,
    ) -> None:
        """Test user creation."""
        user = User(
            oidc_sub="oidc|new123",
            email="new@example.com",
            name="New User",
            role="viewer",
        )

        created = await repository.create(user)

        assert created.id is not None
        assert created.oidc_sub == "oidc|new123"
        assert created.email == "new@example.com"
        assert created.name == "New User"
        assert created.role == "viewer"

    @pytest.mark.asyncio
    async def test_get_by_id(
        self,
        repository: UserRepository,
        test_user: User,
    ) -> None:
        """Test getting user by ID."""
        found = await repository.get_by_id(test_user.id)

        assert found is not None
        assert found.id == test_user.id
        assert found.email == test_user.email

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(
        self,
        repository: UserRepository,
    ) -> None:
        """Test getting non-existent user by ID."""
        found = await repository.get_by_id(uuid4())
        assert found is None

    @pytest.mark.asyncio
    async def test_get_by_oidc_sub(
        self,
        repository: UserRepository,
        test_user: User,
    ) -> None:
        """Test getting user by OIDC subject."""
        found = await repository.get_by_oidc_sub(test_user.oidc_sub)

        assert found is not None
        assert found.oidc_sub == test_user.oidc_sub

    @pytest.mark.asyncio
    async def test_get_by_oidc_sub_not_found(
        self,
        repository: UserRepository,
    ) -> None:
        """Test getting non-existent user by OIDC subject."""
        found = await repository.get_by_oidc_sub("oidc|nonexistent")
        assert found is None

    @pytest.mark.asyncio
    async def test_get_by_email(
        self,
        repository: UserRepository,
        test_user: User,
    ) -> None:
        """Test getting user by email."""
        found = await repository.get_by_email(test_user.email)

        assert found is not None
        assert found.email == test_user.email

    @pytest.mark.asyncio
    async def test_get_by_email_not_found(
        self,
        repository: UserRepository,
    ) -> None:
        """Test getting non-existent user by email."""
        found = await repository.get_by_email("nonexistent@example.com")
        assert found is None

    @pytest.mark.asyncio
    async def test_update_user(
        self,
        repository: UserRepository,
        test_user: User,
    ) -> None:
        """Test user update."""
        test_user.name = "Updated Name"
        updated = await repository.update(test_user)

        assert updated.name == "Updated Name"

    @pytest.mark.asyncio
    async def test_upsert_creates_new_user(
        self,
        repository: UserRepository,
    ) -> None:
        """Test upsert creates new user when not found."""
        user = await repository.upsert_from_oidc(
            oidc_sub="oidc|upsert123",
            email="upsert@example.com",
            name="Upsert User",
        )

        assert user.id is not None
        assert user.oidc_sub == "oidc|upsert123"
        assert user.email == "upsert@example.com"
        assert user.name == "Upsert User"
        assert user.role == "viewer"  # Default role

    @pytest.mark.asyncio
    async def test_upsert_updates_existing_user(
        self,
        repository: UserRepository,
        test_user: User,
    ) -> None:
        """Test upsert updates existing user."""
        user = await repository.upsert_from_oidc(
            oidc_sub=test_user.oidc_sub,
            email="updated@example.com",
            name="Updated Name",
        )

        assert user.id == test_user.id
        assert user.email == "updated@example.com"
        assert user.name == "Updated Name"
        # Role should not change on upsert
        assert user.role == test_user.role
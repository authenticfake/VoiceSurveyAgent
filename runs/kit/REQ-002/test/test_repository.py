"""Tests for user repository."""

import pytest
import pytest_asyncio
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User, UserRole
from app.auth.repository import UserRepository
from app.auth.schemas import UserCreate, UserUpdate

@pytest_asyncio.fixture
async def user_repo(db_session: AsyncSession) -> UserRepository:
    """Create user repository."""
    return UserRepository(db_session)

class TestUserRepository:
    """Tests for UserRepository class."""

    @pytest.mark.asyncio
    async def test_create_user(self, user_repo: UserRepository) -> None:
        """Test creating a new user."""
        user_data = UserCreate(
            oidc_sub="new-oidc-sub",
            email="new@example.com",
            name="New User",
            role=UserRole.VIEWER,
        )

        user = await user_repo.create(user_data)

        assert user.id is not None
        assert user.oidc_sub == "new-oidc-sub"
        assert user.email == "new@example.com"
        assert user.name == "New User"
        assert user.role == UserRole.VIEWER

    @pytest.mark.asyncio
    async def test_get_by_id(
        self, user_repo: UserRepository, test_user: User
    ) -> None:
        """Test getting user by ID."""
        user = await user_repo.get_by_id(test_user.id)

        assert user is not None
        assert user.id == test_user.id
        assert user.email == test_user.email

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, user_repo: UserRepository) -> None:
        """Test getting non-existent user by ID."""
        user = await user_repo.get_by_id(uuid4())
        assert user is None

    @pytest.mark.asyncio
    async def test_get_by_oidc_sub(
        self, user_repo: UserRepository, test_user: User
    ) -> None:
        """Test getting user by OIDC subject."""
        user = await user_repo.get_by_oidc_sub(test_user.oidc_sub)

        assert user is not None
        assert user.oidc_sub == test_user.oidc_sub

    @pytest.mark.asyncio
    async def test_get_by_email(
        self, user_repo: UserRepository, test_user: User
    ) -> None:
        """Test getting user by email."""
        user = await user_repo.get_by_email(test_user.email)

        assert user is not None
        assert user.email == test_user.email

    @pytest.mark.asyncio
    async def test_update_user(
        self, user_repo: UserRepository, test_user: User
    ) -> None:
        """Test updating a user."""
        update_data = UserUpdate(name="Updated Name", role=UserRole.ADMIN)

        updated_user = await user_repo.update(test_user, update_data)

        assert updated_user.name == "Updated Name"
        assert updated_user.role == UserRole.ADMIN

    @pytest.mark.asyncio
    async def test_upsert_creates_new_user(self, user_repo: UserRepository) -> None:
        """Test upsert creates new user when not exists."""
        user = await user_repo.upsert_from_oidc(
            oidc_sub="upsert-new-sub",
            email="upsert@example.com",
            name="Upsert User",
        )

        assert user.id is not None
        assert user.oidc_sub == "upsert-new-sub"
        assert user.email == "upsert@example.com"
        assert user.role == UserRole.VIEWER  # Default role

    @pytest.mark.asyncio
    async def test_upsert_updates_existing_user(
        self, user_repo: UserRepository, test_user: User
    ) -> None:
        """Test upsert updates existing user."""
        user = await user_repo.upsert_from_oidc(
            oidc_sub=test_user.oidc_sub,
            email="updated@example.com",
            name="Updated Name",
        )

        assert user.id == test_user.id
        assert user.email == "updated@example.com"
        assert user.name == "Updated Name"
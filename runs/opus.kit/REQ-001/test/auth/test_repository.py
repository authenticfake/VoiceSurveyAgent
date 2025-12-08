"""Tests for user repository."""

from __future__ import annotations

import uuid

import pytest

from app.auth.domain import User, UserCreate, UserRole, UserUpdate
from app.auth.repository import InMemoryUserRepository


class TestInMemoryUserRepository:
    """Tests for in-memory user repository."""

    @pytest.fixture
    def repo(self) -> InMemoryUserRepository:
        """Create repository instance."""
        return InMemoryUserRepository()

    @pytest.mark.asyncio
    async def test_create_user(self, repo: InMemoryUserRepository) -> None:
        """Test creating a user."""
        user_data = UserCreate(
            oidc_sub="sub-123",
            email="test@example.com",
            name="Test User",
        )
        user = await repo.create(user_data)

        assert user.oidc_sub == "sub-123"
        assert user.email == "test@example.com"
        assert user.role == UserRole.VIEWER

    @pytest.mark.asyncio
    async def test_get_by_id(self, repo: InMemoryUserRepository) -> None:
        """Test getting user by ID."""
        user_data = UserCreate(
            oidc_sub="sub-123",
            email="test@example.com",
            name="Test User",
        )
        created = await repo.create(user_data)
        found = await repo.get_by_id(created.id)

        assert found is not None
        assert found.id == created.id

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, repo: InMemoryUserRepository) -> None:
        """Test getting non-existent user by ID."""
        found = await repo.get_by_id(uuid.uuid4())
        assert found is None

    @pytest.mark.asyncio
    async def test_get_by_oidc_sub(self, repo: InMemoryUserRepository) -> None:
        """Test getting user by OIDC subject."""
        user_data = UserCreate(
            oidc_sub="sub-123",
            email="test@example.com",
            name="Test User",
        )
        await repo.create(user_data)
        found = await repo.get_by_oidc_sub("sub-123")

        assert found is not None
        assert found.oidc_sub == "sub-123"

    @pytest.mark.asyncio
    async def test_get_by_email(self, repo: InMemoryUserRepository) -> None:
        """Test getting user by email."""
        user_data = UserCreate(
            oidc_sub="sub-123",
            email="Test@Example.com",
            name="Test User",
        )
        await repo.create(user_data)
        found = await repo.get_by_email("test@example.com")

        assert found is not None
        assert found.email == "Test@Example.com"

    @pytest.mark.asyncio
    async def test_update_user(self, repo: InMemoryUserRepository) -> None:
        """Test updating a user."""
        user_data = UserCreate(
            oidc_sub="sub-123",
            email="test@example.com",
            name="Test User",
        )
        created = await repo.create(user_data)

        updated = await repo.update(
            created.id, UserUpdate(name="Updated Name", role=UserRole.ADMIN)
        )

        assert updated is not None
        assert updated.name == "Updated Name"
        assert updated.role == UserRole.ADMIN

    @pytest.mark.asyncio
    async def test_update_nonexistent_user(self, repo: InMemoryUserRepository) -> None:
        """Test updating non-existent user."""
        result = await repo.update(uuid.uuid4(), UserUpdate(name="New"))
        assert result is None

    @pytest.mark.asyncio
    async def test_upsert_creates_new(self, repo: InMemoryUserRepository) -> None:
        """Test upsert creates new user."""
        user = await repo.upsert_from_oidc(
            oidc_sub="new-sub",
            email="new@example.com",
            name="New User",
            default_role=UserRole.CAMPAIGN_MANAGER,
        )

        assert user.oidc_sub == "new-sub"
        assert user.role == UserRole.CAMPAIGN_MANAGER

    @pytest.mark.asyncio
    async def test_upsert_updates_existing(self, repo: InMemoryUserRepository) -> None:
        """Test upsert updates existing user."""
        # Create initial user
        await repo.upsert_from_oidc(
            oidc_sub="existing-sub",
            email="old@example.com",
            name="Old Name",
        )

        # Upsert with new info
        user = await repo.upsert_from_oidc(
            oidc_sub="existing-sub",
            email="new@example.com",
            name="New Name",
        )

        assert user.email == "new@example.com"
        assert user.name == "New Name"

    @pytest.mark.asyncio
    async def test_clear(self, repo: InMemoryUserRepository) -> None:
        """Test clearing repository."""
        await repo.create(
            UserCreate(oidc_sub="sub", email="test@example.com", name="Test")
        )
        repo.clear()

        found = await repo.get_by_oidc_sub("sub")
        assert found is None
"""Tests for auth domain models."""

from __future__ import annotations

import uuid
from datetime import datetime

import pytest

from app.auth.domain import RBACPolicy, User, UserCreate, UserRole, UserUpdate


class TestUserRole:
    """Tests for UserRole enum."""

    def test_role_values(self) -> None:
        """Test role enum values."""
        assert UserRole.ADMIN.value == "admin"
        assert UserRole.CAMPAIGN_MANAGER.value == "campaign_manager"
        assert UserRole.VIEWER.value == "viewer"

    def test_role_from_string(self) -> None:
        """Test creating role from string."""
        assert UserRole("admin") == UserRole.ADMIN
        assert UserRole("campaign_manager") == UserRole.CAMPAIGN_MANAGER
        assert UserRole("viewer") == UserRole.VIEWER


class TestRBACPolicy:
    """Tests for RBAC policy."""

    def test_can_read_all_roles(self) -> None:
        """Test all roles can read."""
        assert RBACPolicy.can_read(UserRole.ADMIN) is True
        assert RBACPolicy.can_read(UserRole.CAMPAIGN_MANAGER) is True
        assert RBACPolicy.can_read(UserRole.VIEWER) is True

    def test_can_write_admin_and_manager(self) -> None:
        """Test only admin and campaign_manager can write."""
        assert RBACPolicy.can_write(UserRole.ADMIN) is True
        assert RBACPolicy.can_write(UserRole.CAMPAIGN_MANAGER) is True
        assert RBACPolicy.can_write(UserRole.VIEWER) is False

    def test_is_admin_only_admin(self) -> None:
        """Test only admin has admin permissions."""
        assert RBACPolicy.is_admin(UserRole.ADMIN) is True
        assert RBACPolicy.is_admin(UserRole.CAMPAIGN_MANAGER) is False
        assert RBACPolicy.is_admin(UserRole.VIEWER) is False


class TestUser:
    """Tests for User model."""

    def test_user_creation(self) -> None:
        """Test creating a user."""
        user = User(
            oidc_sub="test-sub",
            email="test@example.com",
            name="Test User",
        )
        assert user.oidc_sub == "test-sub"
        assert user.email == "test@example.com"
        assert user.name == "Test User"
        assert user.role == UserRole.VIEWER  # default
        assert isinstance(user.id, uuid.UUID)
        assert isinstance(user.created_at, datetime)

    def test_user_with_role(self) -> None:
        """Test creating user with specific role."""
        user = User(
            oidc_sub="admin-sub",
            email="admin@example.com",
            name="Admin",
            role=UserRole.ADMIN,
        )
        assert user.role == UserRole.ADMIN


class TestUserCreate:
    """Tests for UserCreate schema."""

    def test_user_create_minimal(self) -> None:
        """Test minimal user create."""
        data = UserCreate(
            oidc_sub="sub-123",
            email="user@example.com",
            name="User",
        )
        assert data.oidc_sub == "sub-123"
        assert data.role is None

    def test_user_create_with_role(self) -> None:
        """Test user create with role."""
        data = UserCreate(
            oidc_sub="sub-123",
            email="user@example.com",
            name="User",
            role=UserRole.CAMPAIGN_MANAGER,
        )
        assert data.role == UserRole.CAMPAIGN_MANAGER


class TestUserUpdate:
    """Tests for UserUpdate schema."""

    def test_user_update_partial(self) -> None:
        """Test partial user update."""
        data = UserUpdate(name="New Name")
        assert data.name == "New Name"
        assert data.email is None
        assert data.role is None

    def test_user_update_role(self) -> None:
        """Test updating role."""
        data = UserUpdate(role=UserRole.ADMIN)
        assert data.role == UserRole.ADMIN
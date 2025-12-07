from __future__ import annotations

from app.auth.domain import map_roles_from_claims, UserRole


def test_explicit_role_claim_takes_precedence():
    claims = {"sub": "123", "email": "u@example.com", "role": "admin"}
    role = map_roles_from_claims(claims)
    assert role == UserRole.ADMIN


def test_group_based_mapping_to_campaign_manager():
    claims = {"sub": "123", "email": "u@example.com", "groups": ["survey_manager"]}
    role = map_roles_from_claims(claims)
    assert role == UserRole.CAMPAIGN_MANAGER


def test_falls_back_to_viewer():
    claims = {"sub": "123", "email": "u@example.com"}
    role = map_roles_from_claims(claims)
    assert role == UserRole.VIEWER
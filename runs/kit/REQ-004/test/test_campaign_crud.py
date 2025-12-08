"""
Tests for Campaign CRUD API endpoints.

Tests cover:
- POST /api/campaigns creates campaign in draft status
- GET /api/campaigns returns paginated list with status filter
- GET /api/campaigns/{id} returns full campaign details
- PUT /api/campaigns/{id} validates field changes against current status
- DELETE /api/campaigns/{id} performs soft delete
- Status transitions follow state machine rules
"""

from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.campaigns.models import Campaign, CampaignStatusEnum

class TestCreateCampaign:
    """Tests for POST /api/campaigns endpoint."""

    @pytest.mark.asyncio
    async def test_create_campaign_success(
        self,
        client: AsyncClient,
        campaign_manager_token: str,
        valid_campaign_data: dict,
    ):
        """Test successful campaign creation in draft status."""
        response = await client.post(
            "/api/campaigns",
            json=valid_campaign_data,
            headers={"Authorization": f"Bearer {campaign_manager_token}"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == valid_campaign_data["name"]
        assert data["status"] == "draft"
        assert data["question_1_text"] == valid_campaign_data["question_1"]["text"]
        assert data["question_1_type"] == valid_campaign_data["question_1"]["type"]
        assert "id" in data
        assert "created_at" in data

    @pytest.mark.asyncio
    async def test_create_campaign_admin_success(
        self,
        client: AsyncClient,
        admin_token: str,
        valid_campaign_data: dict,
    ):
        """Test admin can create campaigns."""
        response = await client.post(
            "/api/campaigns",
            json=valid_campaign_data,
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_create_campaign_viewer_forbidden(
        self,
        client: AsyncClient,
        viewer_token: str,
        valid_campaign_data: dict,
    ):
        """Test viewer cannot create campaigns."""
        response = await client.post(
            "/api/campaigns",
            json=valid_campaign_data,
            headers={"Authorization": f"Bearer {viewer_token}"},
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_create_campaign_no_auth(
        self,
        client: AsyncClient,
        valid_campaign_data: dict,
    ):
        """Test unauthenticated request is rejected."""
        response = await client.post(
            "/api/campaigns",
            json=valid_campaign_data,
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_campaign_invalid_time_window(
        self,
        client: AsyncClient,
        campaign_manager_token: str,
        valid_campaign_data: dict,
    ):
        """Test validation fails when end time is before start time."""
        valid_campaign_data["allowed_call_start_local"] = "20:00:00"
        valid_campaign_data["allowed_call_end_local"] = "09:00:00"

        response = await client.post(
            "/api/campaigns",
            json=valid_campaign_data,
            headers={"Authorization": f"Bearer {campaign_manager_token}"},
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_campaign_invalid_max_attempts(
        self,
        client: AsyncClient,
        campaign_manager_token: str,
        valid_campaign_data: dict,
    ):
        """Test validation fails for invalid max_attempts."""
        valid_campaign_data["max_attempts"] = 10  # Max is 5

        response = await client.post(
            "/api/campaigns",
            json=valid_campaign_data,
            headers={"Authorization": f"Bearer {campaign_manager_token}"},
        )

        assert response.status_code == 422

class TestListCampaigns:
    """Tests for GET /api/campaigns endpoint."""

    @pytest.mark.asyncio
    async def test_list_campaigns_empty(
        self,
        client: AsyncClient,
        viewer_token: str,
    ):
        """Test listing campaigns when none exist."""
        response = await client.get(
            "/api/campaigns",
            headers={"Authorization": f"Bearer {viewer_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0
        assert data["page"] == 1

    @pytest.mark.asyncio
    async def test_list_campaigns_with_data(
        self,
        client: AsyncClient,
        viewer_token: str,
        test_campaign: Campaign,
    ):
        """Test listing campaigns returns existing campaigns."""
        response = await client.get(
            "/api/campaigns",
            headers={"Authorization": f"Bearer {viewer_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert len(data["items"]) >= 1

    @pytest.mark.asyncio
    async def test_list_campaigns_with_status_filter(
        self,
        client: AsyncClient,
        viewer_token: str,
        test_campaign: Campaign,
    ):
        """Test filtering campaigns by status."""
        response = await client.get(
            "/api/campaigns?status=draft",
            headers={"Authorization": f"Bearer {viewer_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert item["status"] == "draft"

    @pytest.mark.asyncio
    async def test_list_campaigns_pagination(
        self,
        client: AsyncClient,
        viewer_token: str,
    ):
        """Test pagination parameters."""
        response = await client.get(
            "/api/campaigns?page=1&page_size=5",
            headers={"Authorization": f"Bearer {viewer_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 5

class TestGetCampaign:
    """Tests for GET /api/campaigns/{id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_campaign_success(
        self,
        client: AsyncClient,
        viewer_token: str,
        test_campaign: Campaign,
    ):
        """Test getting campaign details."""
        response = await client.get(
            f"/api/campaigns/{test_campaign.id}",
            headers={"Authorization": f"Bearer {viewer_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_campaign.id)
        assert data["name"] == test_campaign.name
        assert data["status"] == test_campaign.status

    @pytest.mark.asyncio
    async def test_get_campaign_not_found(
        self,
        client: AsyncClient,
        viewer_token: str,
    ):
        """Test 404 for non-existent campaign."""
        response = await client.get(
            f"/api/campaigns/{uuid4()}",
            headers={"Authorization": f"Bearer {viewer_token}"},
        )

        assert response.status_code == 404

class TestUpdateCampaign:
    """Tests for PUT /api/campaigns/{id} endpoint."""

    @pytest.mark.asyncio
    async def test_update_campaign_draft_success(
        self,
        client: AsyncClient,
        campaign_manager_token: str,
        test_campaign: Campaign,
    ):
        """Test updating campaign in draft status."""
        update_data = {
            "name": "Updated Campaign Name",
            "description": "Updated description",
        }

        response = await client.put(
            f"/api/campaigns/{test_campaign.id}",
            json=update_data,
            headers={"Authorization": f"Bearer {campaign_manager_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == update_data["name"]
        assert data["description"] == update_data["description"]

    @pytest.mark.asyncio
    async def test_update_campaign_viewer_forbidden(
        self,
        client: AsyncClient,
        viewer_token: str,
        test_campaign: Campaign,
    ):
        """Test viewer cannot update campaigns."""
        response = await client.put(
            f"/api/campaigns/{test_campaign.id}",
            json={"name": "New Name"},
            headers={"Authorization": f"Bearer {viewer_token}"},
        )

        assert response.status_code == 403

class TestDeleteCampaign:
    """Tests for DELETE /api/campaigns/{id} endpoint."""

    @pytest.mark.asyncio
    async def test_delete_campaign_success(
        self,
        client: AsyncClient,
        campaign_manager_token: str,
        test_campaign: Campaign,
    ):
        """Test soft deleting a campaign."""
        response = await client.delete(
            f"/api/campaigns/{test_campaign.id}",
            headers={"Authorization": f"Bearer {campaign_manager_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_delete_campaign_viewer_forbidden(
        self,
        client: AsyncClient,
        viewer_token: str,
        test_campaign: Campaign,
    ):
        """Test viewer cannot delete campaigns."""
        response = await client.delete(
            f"/api/campaigns/{test_campaign.id}",
            headers={"Authorization": f"Bearer {viewer_token}"},
        )

        assert response.status_code == 403

class TestStatusTransitions:
    """Tests for campaign status transitions."""

    @pytest.mark.asyncio
    async def test_transition_draft_to_running(
        self,
        client: AsyncClient,
        campaign_manager_token: str,
        test_campaign: Campaign,
    ):
        """Test transitioning from draft to running."""
        response = await client.post(
            f"/api/campaigns/{test_campaign.id}/status",
            json={"target_status": "running"},
            headers={"Authorization": f"Bearer {campaign_manager_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"

    @pytest.mark.asyncio
    async def test_transition_draft_to_scheduled(
        self,
        client: AsyncClient,
        campaign_manager_token: str,
        test_campaign: Campaign,
    ):
        """Test transitioning from draft to scheduled."""
        response = await client.post(
            f"/api/campaigns/{test_campaign.id}/status",
            json={"target_status": "scheduled"},
            headers={"Authorization": f"Bearer {campaign_manager_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "scheduled"

    @pytest.mark.asyncio
    async def test_invalid_transition_draft_to_completed(
        self,
        client: AsyncClient,
        campaign_manager_token: str,
        test_campaign: Campaign,
    ):
        """Test invalid transition from draft to completed."""
        response = await client.post(
            f"/api/campaigns/{test_campaign.id}/status",
            json={"target_status": "completed"},
            headers={"Authorization": f"Bearer {campaign_manager_token}"},
        )

        assert response.status_code == 400
        data = response.json()
        assert data["error_code"] == "INVALID_STATE_TRANSITION"

    @pytest.mark.asyncio
    async def test_transition_viewer_forbidden(
        self,
        client: AsyncClient,
        viewer_token: str,
        test_campaign: Campaign,
    ):
        """Test viewer cannot transition campaign status."""
        response = await client.post(
            f"/api/campaigns/{test_campaign.id}/status",
            json={"target_status": "running"},
            headers={"Authorization": f"Bearer {viewer_token}"},
        )

        assert response.status_code == 403
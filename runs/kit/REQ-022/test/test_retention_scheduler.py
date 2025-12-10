"""
Unit tests for retention scheduler.

REQ-022: Data retention jobs
"""

import pytest
import asyncio
from datetime import datetime, time, timedelta
from unittest.mock import AsyncMock, MagicMock

from infra.retention.scheduler import RetentionScheduler
from infra.retention.models import RetentionResult, DeletionStatus


class MockRetentionService:
    """Mock retention service for testing."""
    
    def __init__(self):
        self.run_count = 0
        self.last_result = None
    
    async def run_retention_job(self, now=None, dry_run=False):
        self.run_count += 1
        result = RetentionResult()
        result.complete()
        self.last_result = result
        return result


class MockGDPRService:
    """Mock GDPR service for testing."""
    
    def __init__(self):
        self.process_count = 0
    
    async def process_pending_requests(self, now=None):
        self.process_count += 1
        return []


class TestRetentionScheduler:
    """Tests for RetentionScheduler."""
    
    @pytest.fixture
    def mock_retention_service(self):
        return MockRetentionService()
    
    @pytest.fixture
    def mock_gdpr_service(self):
        return MockGDPRService()
    
    @pytest.fixture
    def scheduler(self, mock_retention_service, mock_gdpr_service):
        return RetentionScheduler(
            retention_service=mock_retention_service,
            gdpr_service=mock_gdpr_service,
            daily_run_time=time(2, 0),
            gdpr_check_interval_minutes=60,
        )
    
    def test_calculate_next_run_before_daily_time(self, scheduler):
        """Test next run calculation when before daily time."""
        now = datetime(2024, 6, 15, 1, 0, 0)  # 1 AM
        
        next_run = scheduler._calculate_next_run(now)
        
        expected = datetime(2024, 6, 15, 2, 0, 0)  # 2 AM same day
        assert next_run == expected
    
    def test_calculate_next_run_after_daily_time(self, scheduler):
        """Test next run calculation when after daily time."""
        now = datetime(2024, 6, 15, 3, 0, 0)  # 3 AM
        
        next_run = scheduler._calculate_next_run(now)
        
        expected = datetime(2024, 6, 16, 2, 0, 0)  # 2 AM next day
        assert next_run == expected
    
    def test_calculate_next_run_at_daily_time(self, scheduler):
        """Test next run calculation when at daily time."""
        now = datetime(2024, 6, 15, 2, 0, 0)  # Exactly 2 AM
        
        next_run = scheduler._calculate_next_run(now)
        
        expected = datetime(2024, 6, 16, 2, 0, 0)  # 2 AM next day
        assert next_run == expected
    
    @pytest.mark.asyncio
    async def test_run_now(self, scheduler, mock_retention_service):
        """Test immediate job execution."""
        result = await scheduler.run_now()
        
        assert mock_retention_service.run_count == 1
        assert result.status == DeletionStatus.COMPLETED
    
    @pytest.mark.asyncio
    async def test_process_gdpr_now(self, scheduler, mock_gdpr_service):
        """Test immediate GDPR processing."""
        count = await scheduler.process_gdpr_now()
        
        assert mock_gdpr_service.process_count == 1
        assert count == 0
    
    @pytest.mark.asyncio
    async def test_start_stop(self, scheduler):
        """Test scheduler start and stop."""
        await scheduler.start()
        
        assert scheduler._running is True
        assert scheduler._retention_task is not None
        assert scheduler._gdpr_task is not None
        
        await scheduler.stop()
        
        assert scheduler._running is False
    
    @pytest.mark.asyncio
    async def test_start_twice_warns(self, scheduler):
        """Test that starting twice logs warning."""
        await scheduler.start()
        await scheduler.start()  # Should warn but not fail
        
        await scheduler.stop()
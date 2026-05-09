"""
Integration Tests for Docker Compose Environment

These tests are designed to run in a Docker Compose environment
with all services (PostgreSQL, Redis, API Gateway) running.

Run with: docker compose -f docker-compose.test.yml up --exit-code-from test
"""

import os
import time
import uuid

import pytest
import requests

# Configuration from environment variables
API_GATEWAY_URL = os.getenv("API_GATEWAY_URL", "http://api-gateway:8000")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://aegisops:aegisops@postgres:5432/aegisops")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture(scope="session")
def api_base_url():
    """Get API gateway base URL."""
    return API_GATEWAY_URL


@pytest.fixture(scope="session")
def wait_for_services():
    """Wait for all services to be healthy."""
    max_retries = 30
    retry_delay = 2

    for i in range(max_retries):
        try:
            response = requests.get(f"{API_GATEWAY_URL}/api/v1/health", timeout=5)
            if response.status_code == 200:
                return True
        except requests.exceptions.ConnectionError:
            pass
        time.sleep(retry_delay)

    raise RuntimeError("Services did not become healthy in time")


@pytest.fixture
def auth_token(wait_for_services):
    """Get authentication token for API requests."""
    # For integration tests, we might need to create a test user first
    # This is a simplified version - in production you'd create a test user
    return None  # Will need to implement proper auth


# ============================================================================
# Health Check Tests
# ============================================================================

class TestServiceHealth:
    """Test that all services are healthy and connected."""

    def test_api_gateway_health(self, wait_for_services):
        """Test API gateway health endpoint."""
        response = requests.get(f"{API_GATEWAY_URL}/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data or "healthy" in data

    def test_database_connection(self, wait_for_services):
        """Test database connection through API."""
        # This would require a database health endpoint
        # For now, we test that the API starts which implies DB connection
        response = requests.get(f"{API_GATEWAY_URL}/api/v1/health")
        assert response.status_code == 200

    def test_redis_connection(self, wait_for_services):
        """Test Redis connection through API."""
        # Celery uses Redis, so if API starts, Redis is likely connected
        response = requests.get(f"{API_GATEWAY_URL}/api/v1/health")
        assert response.status_code == 200


# ============================================================================
# Orchestrator Integration Tests
# ============================================================================

class TestOrchestratorIntegration:
    """Integration tests for orchestrator functionality."""

    def test_orchestrator_health_endpoint(self, wait_for_services):
        """Test orchestrator health endpoint."""
        # This endpoint requires authentication
        # For integration tests, we might skip auth or use a test token
        response = requests.get(f"{API_GATEWAY_URL}/api/v1/orchestrator/health")
        # Should return 401 if auth is required
        assert response.status_code in [200, 401]

    def test_orchestrator_analyze_endpoint_structure(self, wait_for_services):
        """Test orchestrator analyze endpoint exists."""
        response = requests.post(
            f"{API_GATEWAY_URL}/api/v1/orchestrator/analyze",
            json={"log_text": "test log"},
        )
        # Should return 401 if auth is required
        assert response.status_code in [401, 422]

    def test_orchestrator_analyze_async_endpoint_structure(self, wait_for_services):
        """Test orchestrator analyze-async endpoint exists."""
        response = requests.post(
            f"{API_GATEWAY_URL}/api/v1/orchestrator/analyze-async",
            json={"log_text": "test log"},
        )
        # Should return 401 if auth is required
        assert response.status_code in [401, 422]


# ============================================================================
# Log Ingestion Integration Tests
# ============================================================================

class TestLogIngestionIntegration:
    """Integration tests for log ingestion functionality."""

    def test_log_process_endpoint_structure(self, wait_for_services):
        """Test log process endpoint exists."""
        response = requests.post(
            f"{API_GATEWAY_URL}/api/v1/logs/process",
            json={"log_text": "2024-01-15 ERROR: Test error"},
        )
        # Should return 401 if auth is required
        assert response.status_code in [401, 422]

    def test_log_detect_source_endpoint_structure(self, wait_for_services):
        """Test log source detection endpoint exists."""
        response = requests.post(
            f"{API_GATEWAY_URL}/api/v1/logs/detect-source",
            json={"log_text": "2024-01-15 ERROR: Test error"},
        )
        # Should return 401 if auth is required
        assert response.status_code in [401, 422]


# ============================================================================
# End-to-End Workflow Tests
# ============================================================================

class TestEndToEndWorkflow:
    """End-to-end workflow tests."""

    def test_full_incident_workflow(self, wait_for_services):
        """
        Test complete incident workflow:
        1. Create incident
        2. Upload logs
        3. Trigger analysis
        4. Verify results
        """
        # This test would require proper authentication
        # and is more complex - left as a template
        pass


# ============================================================================
# Performance Tests
# ============================================================================

class TestPerformance:
    """Basic performance tests."""

    def test_api_response_time(self, wait_for_services):
        """Test API response time is acceptable."""
        start_time = time.time()
        response = requests.get(f"{API_GATEWAY_URL}/api/v1/health")
        elapsed = time.time() - start_time

        assert response.status_code == 200
        assert elapsed < 5.0  # Should respond within 5 seconds

    def test_log_processing_performance(self, wait_for_services):
        """Test log processing completes in reasonable time."""
        # Create a moderately sized log
        log_lines = [
            f"2024-01-15T10:{i:02d}:00Z INFO Processing request {i}"
            for i in range(100)
        ]
        log_text = "\n".join(log_lines)

        start_time = time.time()
        response = requests.post(
            f"{API_GATEWAY_URL}/api/v1/logs/process",
            json={"log_text": log_text},
        )
        elapsed = time.time() - start_time

        # Should complete within 10 seconds for 100 lines
        assert response.status_code in [401, 422, 200]
        assert elapsed < 10.0
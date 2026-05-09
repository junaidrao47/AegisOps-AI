"""
Tests for AI Orchestrator Integration

Tests for the orchestrator service, API routes, and ingestion hooks.
"""

import os
from unittest.mock import MagicMock, patch

import pytest

from app.core.config import settings
from app.schemas.orchestrator import (
    OrchestratorAnalyzeRequest,
    OrchestratorAnalyzeResponse,
    OrchestratorHealthResponse,
)


# ============================================================================
# Sample Data
# ============================================================================

SAMPLE_KUBERNETES_LOG = """
2024-01-15T10:30:00Z [kubelet] Pod my-app-5d4f8b7c9-x2v4n status changed to CrashLoopBackOff
2024-01-15T10:30:05Z [kubelet] Back-off restarting failed container
2024-01-15T10:30:10Z [kubectl] Error from server: container "my-app" in pod "my-app-5d4f8b7c9-x2v4n" is waiting to start: CrashLoopBackOff
2024-01-15T10:31:00Z [kubelet] Container my-app OOMKilled - out of memory
"""

SAMPLE_PAYLOAD = {
    "incident_type": "kubernetes",
    "summary": "API pods are crashing",
    "log_text": SAMPLE_KUBERNETES_LOG,
    "tags": ["k8s", "production"],
}


# ============================================================================
# Orchestrator Service Tests
# ============================================================================

class TestOrchestratorService:
    """Tests for app.services.orchestrator module."""

    def test_run_orchestrator_disabled(self, monkeypatch):
        """Test that run_orchestrator raises when disabled."""
        # We need to patch the settings module's environment variable
        monkeypatch.setenv("ORCHESTRATOR_ENABLED", "false")
        # Reload the settings module to pick up the change
        import importlib
        import app.core.config as config_module
        importlib.reload(config_module)

        from app.services.orchestrator import run_orchestrator

        with pytest.raises(RuntimeError, match="orchestrator_disabled"):
            run_orchestrator(SAMPLE_PAYLOAD)

        # Reload back to original
        monkeypatch.setenv("ORCHESTRATOR_ENABLED", "true")
        importlib.reload(config_module)

    def test_get_orchestrator_health(self):
        """Test health check returns expected structure."""
        from app.services.orchestrator import get_orchestrator_health

        health = get_orchestrator_health()

        assert isinstance(health, dict)
        assert "enabled" in health
        assert "available" in health
        assert "path" in health
        assert "auto_analyze_logs" in health

    def test_reset_orchestrator_cache(self):
        """Test cache reset doesn't raise."""
        from app.services.orchestrator import reset_orchestrator_cache

        # Should not raise
        reset_orchestrator_cache()

    def test_run_orchestrator_with_mock(self):
        """Test run_orchestrator with mocked imports."""
        # Create mock modules
        mock_context = MagicMock()
        mock_context.summary = "Test summary"
        mock_context.recommendations = ["Fix the issue"]
        mock_context.agent_results = {
            "log_analysis": MagicMock(
                summary="Log analysis summary",
                findings=["Finding 1"],
                confidence=0.9,
                evidence=["Evidence 1"],
            )
        }
        mock_context.errors = []

        mock_graph = MagicMock(return_value=mock_context)
        mock_incident_context = MagicMock(return_value=mock_context)

        # Patch both settings and the orchestrator modules
        with patch("app.services.orchestrator.settings") as mock_settings, \
             patch("app.services.orchestrator._orchestrator_modules", {
                 "IncidentContext": mock_incident_context,
                 "build_graph": MagicMock(return_value=mock_graph),
             }):
            mock_settings.orchestrator_enabled = True

            from app.services.orchestrator import run_orchestrator

            result = run_orchestrator(SAMPLE_PAYLOAD, incident_id=123)

            assert result["incident_id"] == 123
            assert result["summary"] == "Test summary"
            assert result["recommendations"] == ["Fix the issue"]
            assert "log_analysis" in result["agent_results"]
            assert result["errors"] == []


# ============================================================================
# Ingestion Service Tests
# ============================================================================

class TestIngestionService:
    """Tests for app.services.ingestion_service module."""

    def test_validate_upload_missing_filename(self):
        """Test validation fails for missing filename."""
        from app.services.ingestion_service import validate_upload

        with pytest.raises(ValueError, match="filename is required"):
            validate_upload("")

    def test_validate_upload_valid_filename(self):
        """Test validation passes for valid filename."""
        from app.services.ingestion_service import validate_upload

        # Should not raise
        validate_upload("test.log")

    def test_trigger_auto_analysis_empty_log(self):
        """Test auto-analysis handles empty log text."""
        from app.services.ingestion_service import trigger_auto_analysis

        result = trigger_auto_analysis("")
        assert result is None

    def test_trigger_auto_analysis_success(self):
        """Test auto-analysis returns results when successful."""
        mock_result = {
            "incident_id": 1,
            "summary": "AI summary",
            "recommendations": ["Recommendation 1"],
            "agent_results": {},
            "errors": [],
        }

        with patch("app.services.orchestrator.run_orchestrator", return_value=mock_result) as mock_run:
            from app.services.ingestion_service import trigger_auto_analysis

            result = trigger_auto_analysis(
                SAMPLE_KUBERNETES_LOG,
                incident_id=1,
                source_type="kubernetes",
            )

            assert result is not None
            assert result["summary"] == "AI summary"
            mock_run.assert_called_once()

    def test_trigger_auto_analysis_async(self):
        """Test async auto-analysis queues task."""
        mock_result = {"task_id": "abc123", "status": "queued"}

        with patch("app.services.orchestrator.run_orchestrator_async", return_value=mock_result) as mock_run_async:
            from app.services.ingestion_service import trigger_auto_analysis_async

            result = trigger_auto_analysis_async(
                SAMPLE_KUBERNETES_LOG,
                incident_id=1,
                source_type="kubernetes",
            )

            assert result is not None
            assert result["task_id"] == "abc123"
            mock_run_async.assert_called_once()


# ============================================================================
# Celery Task Tests
# ============================================================================

class TestCeleryTasks:
    """Tests for Celery tasks."""

    def test_run_orchestrator_analysis_success(self):
        """Test orchestrator analysis task success."""
        mock_result = {
            "incident_id": 1,
            "summary": "Test",
            "recommendations": [],
            "agent_results": {},
            "errors": [],
        }

        with patch("app.services.orchestrator.run_orchestrator", return_value=mock_result):
            from app.workers.tasks import run_orchestrator_analysis

            result = run_orchestrator_analysis(SAMPLE_PAYLOAD, incident_id=1)

            assert result["success"] is True
            assert "result" in result

    def test_run_orchestrator_analysis_failure(self):
        """Test orchestrator analysis task failure."""
        with patch("app.services.orchestrator.run_orchestrator", side_effect=RuntimeError("Test error")):
            from app.workers.tasks import run_orchestrator_analysis

            result = run_orchestrator_analysis(SAMPLE_PAYLOAD)

            assert result["success"] is False
            assert "error" in result


# ============================================================================
# Schema Tests
# ============================================================================

class TestSchemas:
    """Tests for Pydantic schemas."""

    def test_analyze_request_schema(self):
        """Test OrchestratorAnalyzeRequest schema validation."""
        request = OrchestratorAnalyzeRequest(
            incident_id=1,
            log_text="test log",
            incident_type="kubernetes",
            summary="Test incident",
            tags=["test"],
        )

        assert request.incident_id == 1
        assert request.log_text == "test log"
        assert request.incident_type == "kubernetes"
        assert request.tags == ["test"]

    def test_analyze_request_schema_defaults(self):
        """Test OrchestratorAnalyzeRequest default values."""
        request = OrchestratorAnalyzeRequest()

        assert request.incident_id is None
        assert request.log_text is None
        assert request.tags == []

    def test_analyze_response_schema(self):
        """Test OrchestratorAnalyzeResponse schema."""
        response = OrchestratorAnalyzeResponse(
            incident_id=1,
            summary="Test summary",
            recommendations=["Fix it"],
            agent_results={
                "log_analysis": {
                    "summary": "Log analysis",
                    "findings": ["Error found"],
                    "confidence": 0.95,
                    "evidence": ["Log line 1"],
                }
            },
            errors=[],
        )

        assert response.incident_id == 1
        assert len(response.agent_results) == 1

    def test_health_response_schema(self):
        """Test OrchestratorHealthResponse schema."""
        response = OrchestratorHealthResponse(
            enabled=True,
            available=True,
            path="/path/to/orchestrator",
            auto_analyze_logs=True,
        )

        assert response.enabled is True
        assert response.available is True
        assert response.path == "/path/to/orchestrator"


# ============================================================================
# Integration Tests (API Routes)
# ============================================================================

class TestOrchestratorRoutes:
    """Integration tests for orchestrator API routes."""

    @pytest.fixture
    def client(self):
        """Create test client with mocked dependencies."""
        from fastapi.testclient import TestClient
        from app.main import app

        return TestClient(app)

    def test_health_endpoint_requires_auth(self, client):
        """Test that health endpoint requires authentication."""
        response = client.get("/api/v1/orchestrator/health")
        assert response.status_code == 401

    def test_analyze_endpoint_requires_auth(self, client):
        """Test that analyze endpoint requires authentication."""
        response = client.post(
            "/api/v1/orchestrator/analyze",
            json={"log_text": "test"},
        )
        assert response.status_code == 401

    def test_analyze_async_endpoint_requires_auth(self, client):
        """Test that analyze-async endpoint requires authentication."""
        response = client.post(
            "/api/v1/orchestrator/analyze-async",
            json={"log_text": "test"},
        )
        assert response.status_code == 401


# ============================================================================
# End-to-End Integration Tests
# ============================================================================

class TestEndToEndIntegration:
    """End-to-end tests for the full integration flow."""

    def test_full_analysis_flow_with_mock(self):
        """Test complete analysis flow from request to response."""
        # Mock the orchestrator modules
        mock_context = MagicMock()
        mock_context.summary = "Pod crash detected due to OOM"
        mock_context.recommendations = [
            "Increase memory limits",
            "Check for memory leaks",
        ]
        mock_context.agent_results = {
            "log_analysis": MagicMock(
                summary="OOMKilled detected",
                findings=["OOMKilled", "CrashLoopBackOff"],
                confidence=0.95,
                evidence=["Container my-app OOMKilled"],
            ),
            "kubernetes": MagicMock(
                summary="Kubernetes pod issue",
                findings=["Pod in CrashLoopBackOff"],
                confidence=0.9,
                evidence=["Pod status changed to CrashLoopBackOff"],
            ),
        }
        mock_context.errors = []

        mock_graph = MagicMock(return_value=mock_context)
        mock_incident_context = MagicMock(return_value=mock_context)

        # Patch both settings and the orchestrator modules
        with patch("app.services.orchestrator.settings") as mock_settings, \
             patch("app.services.orchestrator._orchestrator_modules", {
                 "IncidentContext": mock_incident_context,
                 "build_graph": MagicMock(return_value=mock_graph),
             }):
            mock_settings.orchestrator_enabled = True

            from app.services.orchestrator import run_orchestrator

            result = run_orchestrator(SAMPLE_PAYLOAD, incident_id=1)

            assert result["incident_id"] == 1
            assert result["summary"] == "Pod crash detected due to OOM"
            assert len(result["recommendations"]) == 2
            assert "log_analysis" in result["agent_results"]
            assert "kubernetes" in result["agent_results"]

    def test_ingestion_hook_integration(self):
        """Test that ingestion hook properly calls orchestrator."""
        mock_result = {
            "incident_id": 1,
            "summary": "Issues detected",
            "recommendations": ["Fix issues"],
            "agent_results": {},
            "errors": [],
        }

        with patch("app.services.orchestrator.run_orchestrator", return_value=mock_result) as mock_run:
            from app.services.ingestion_service import trigger_auto_analysis

            result = trigger_auto_analysis(
                SAMPLE_KUBERNETES_LOG,
                incident_id=1,
                source_type="kubernetes",
            )

            assert result is not None
            assert result["summary"] == "Issues detected"
            mock_run.assert_called_once()

            # Verify the payload structure
            call_args = mock_run.call_args[0]
            payload = call_args[0]
            assert payload["incident_type"] == "kubernetes"
            assert "auto-analysis" in payload["tags"]
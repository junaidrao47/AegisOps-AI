from aegis_ai.agents.root_cause.agent import analyze_root_cause
from aegis_ai.orchestration.state import IncidentContext, AgentResult


def make_ctx(payload=None, shared_findings=None, agent_results=None) -> IncidentContext:
    return IncidentContext(
        incident_id="test-1",
        payload=payload or {},
        agent_results=agent_results or {},
        shared_context={"findings": shared_findings or [], "evidence": []},
    )


def test_missing_database_url_detected():
    payload = {"message": "Application failed to start: missing DATABASE_URL environment variable"}
    ctx = make_ctx(payload=payload, shared_findings=["missing DATABASE_URL detected in logs"])

    result = analyze_root_cause(ctx)

    assert isinstance(result, AgentResult)
    assert "Missing DATABASE_URL" in " ".join(result.findings) or "DATABASE_URL" in result.summary
    assert result.metadata.get("severity") == "Critical"
    assert 0.0 <= result.confidence <= 1.0

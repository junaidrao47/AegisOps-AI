from __future__ import annotations

from typing import List

from aegis_ai.agents.utils import extract_text
from aegis_ai.orchestration.state import AgentResult, IncidentContext


def analyze_root_cause(ctx: IncidentContext) -> AgentResult:
    """Generate a compact root-cause analysis from shared findings and payload.

    Produces a summary, a list of probable causes, a confidence score, short
    evidence snippets, and metadata containing severity, dependency chain and
    affected systems.
    """
    findings: List[str] = ctx.shared_context.get("findings", [])
    evidence: List[str] = ctx.shared_context.get("evidence", [])
    text = extract_text(ctx.payload, ["message", "summary", "description", "logs", "error", "details"])

    probable: List[str] = []
    dependency: List[str] = []
    affected: List[str] = []
    remediation: List[str] = []

    lowered = (" ".join(findings) + " " + text).lower()

    # heuristic rules for common root causes
    if "database_url" in lowered or "missing database" in lowered or "missing DATABASE_URL" in text:
        probable.append("Missing DATABASE_URL environment variable")
        dependency.append("database: postgres/postgres-compatible service")
        affected.append("application backend / DB-dependent services")
        remediation.append("Set the DATABASE_URL env var and restart the service.")

    if "connection refused" in lowered or "could not connect to" in lowered:
        probable.append("Database or upstream service unreachable (connection refused)")
        dependency.append("network / database endpoint")
        affected.append("backend services relying on DB or upstream APIs")
        remediation.append("Verify network connectivity and that the target service is running.")

    if "out of memory" in lowered or "oom" in lowered:
        probable.append("Out of memory in container/pod")
        dependency.append("container runtime / node resources")
        affected.append("service instance(s) experiencing restarts")
        remediation.append("Increase memory limits and inspect memory usage / leaks.")

    if "imagepullbackoff" in lowered or "image pull" in lowered:
        probable.append("Image pull failure (registry/auth) ")
        dependency.append("container registry / image artifact")
        affected.append("deployment/pods relying on the image")
        remediation.append("Check registry credentials and image tag availability.")

    if "permission denied" in lowered or "access denied" in lowered:
        probable.append("Permission denied when accessing resource")
        dependency.append("iam / service account / secret mount")
        affected.append("operations that require the permission")
        remediation.append("Audit roles and permissions; ensure service accounts and secrets are correct.")

    # fallback: if no heuristics matched, suggest common next steps
    if not probable:
        probable.append("Insufficient signals to determine a single root cause")
        remediation.append("Collect more logs, system metrics and recent deployment history.")

    # Confidence: derive from existing agent confidences if available
    confidences = [r.confidence for r in ctx.agent_results.values()] if ctx.agent_results else []
    if confidences:
        confidence = min(0.99, max(0.3, sum(confidences) / len(confidences)))
    else:
        confidence = 0.5 if probable and probable[0] != "Insufficient signals to determine a single root cause" else 0.35

    severity = "Critical" if any("database" in p.lower() or "out of memory" in p.lower() for p in probable) else "High" if probable else "Medium"

    summary = f"root cause analysis: {probable[0]}" if probable else "root cause analysis inconclusive"

    metadata = {
        "severity": severity,
        "dependency_chain": dependency,
        "affected_systems": affected,
        "remediation_steps": remediation,
    }

    # findings should be human readable bullet-like statements
    rc_findings = [f"Probable cause: {p}" for p in probable]
    rc_findings += [f"Suggested remediation: {r}" for r in remediation[:3]]

    return AgentResult(
        agent="root_cause",
        summary=summary,
        findings=rc_findings,
        confidence=round(confidence, 2),
        evidence=evidence[:3] or _trim_evidence(text),
        metadata=metadata,
    )


def _trim_evidence(text: str, limit: int = 3) -> List[str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return lines[:limit]

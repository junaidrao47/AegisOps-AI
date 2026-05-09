from __future__ import annotations

from aegis_ai.orchestration.state import IncidentContext


def recommend_fixes(ctx: IncidentContext) -> IncidentContext:
    recommendations: list[str] = []

    findings = ctx.shared_context.get("findings", [])
    if findings:
        recommendations.extend(_recommend_from_findings(findings))

    if not recommendations:
        recommendations.append("Collect full logs and confirm the incident scope.")
        recommendations.append("Validate recent changes or deployments in the last 24 hours.")

    ctx.recommendations = recommendations
    return ctx


def _recommend_from_findings(findings: list[str]) -> list[str]:
    text = " ".join(findings).lower()
    suggestions: list[str] = []

    if "oom" in text or "out of memory" in text:
        suggestions.append("Increase pod/container memory limits and inspect memory leaks.")
    if "imagepullbackoff" in text:
        suggestions.append("Verify image registry credentials and image tag availability.")
    if "failed scheduling" in text:
        suggestions.append("Check node capacity and taints; adjust requests/limits or add nodes.")
    if "build failed" in text or "pipeline" in text:
        suggestions.append("Review CI pipeline logs and rollback the last failing change.")
    if "permission denied" in text:
        suggestions.append("Verify service account permissions and secret mounts.")
    if "timeout" in text:
        suggestions.append("Check upstream dependencies and increase timeout thresholds if needed.")
    if "cve" in text or "vulnerab" in text:
        suggestions.append("Patch affected packages and rotate exposed credentials.")

    return suggestions

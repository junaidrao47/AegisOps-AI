from __future__ import annotations

from aegis_ai.agents.utils import extract_text, keyword_hits
from aegis_ai.orchestration.state import AgentResult, IncidentContext


def analyze_kubernetes(ctx: IncidentContext) -> AgentResult:
    text = extract_text(
        ctx.payload,
        ["logs", "kubernetes", "events", "description", "details", "summary"],
    )
    patterns = [
        r"crashloopbackoff",
        r"imagepullbackoff",
        r"oomkilled",
        r"node not ready",
        r"failed scheduling",
        r"pod.*evicted",
        r"back-off restarting failed container",
    ]
    hits = keyword_hits(text, patterns)
    findings = [f"Detected k8s condition: {hit}" for hit in hits]
    summary = "kubernetes analysis complete" if hits else "no critical k8s signals detected"
    confidence = 0.75 if hits else 0.45

    return AgentResult(
        agent="kubernetes",
        summary=summary,
        findings=findings,
        confidence=confidence,
        evidence=_trim_evidence(text),
    )


def _trim_evidence(text: str, limit: int = 3) -> list[str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return lines[:limit]

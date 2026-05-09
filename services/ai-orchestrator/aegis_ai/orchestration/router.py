from __future__ import annotations

from typing import Iterable

from aegis_ai.orchestration.state import IncidentContext


def route(ctx: IncidentContext) -> list[str]:
    """Route incident to the most relevant analysis agents."""

    payload = ctx.payload
    text = _collect_text(payload)
    tags = set(_normalize_list(payload.get("tags", [])))
    incident_type = str(payload.get("incident_type", "")).lower()

    selected: set[str] = set()

    if _match_any(text, ["kubernetes", "k8s", "kubectl", "pod", "node", "helm", "etcd"]):
        selected.add("kubernetes")
    if _match_any(text, ["ci", "cd", "pipeline", "github actions", "gitlab", "jenkins", "build failed"]):
        selected.add("cicd")
    if _match_any(text, ["vulnerab", "cve", "malware", "unauthorized", "exploit", "token leak"]):
        selected.add("security")
    if _match_any(text, ["log", "exception", "traceback", "error", "panic", "stack trace"]):
        selected.add("log_analysis")
    if _match_any(text, ["doc", "runbook", "kb", "knowledge", "procedure"]):
        selected.add("docs_retrieval")

    if incident_type:
        if "kuber" in incident_type:
            selected.add("kubernetes")
        if "ci" in incident_type or "cd" in incident_type:
            selected.add("cicd")
        if "security" in incident_type:
            selected.add("security")

    if "security" in tags:
        selected.add("security")
    if "kubernetes" in tags or "k8s" in tags:
        selected.add("kubernetes")
    if "cicd" in tags or "pipeline" in tags:
        selected.add("cicd")

    if not selected:
        selected.update({"log_analysis", "docs_retrieval"})

    return sorted(selected)


def _collect_text(payload: dict) -> str:
    fields = [
        "message",
        "summary",
        "description",
        "log_text",
        "logs",
        "error",
        "details",
    ]
    parts: list[str] = []
    for field in fields:
        value = payload.get(field)
        if not value:
            continue
        if isinstance(value, str):
            parts.append(value)
        elif isinstance(value, (list, tuple)):
            parts.extend(str(item) for item in value if item)
        elif isinstance(value, dict):
            parts.extend(str(item) for item in value.values() if item)
    return "\n".join(parts)


def _normalize_list(values: Iterable) -> list[str]:
    return [str(value).strip().lower() for value in values if value]


def _match_any(text: str, patterns: list[str]) -> bool:
    lowered = text.lower()
    return any(pattern in lowered for pattern in patterns)

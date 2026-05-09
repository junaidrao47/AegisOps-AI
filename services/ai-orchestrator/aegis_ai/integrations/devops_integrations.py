from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class IntegrationEvent:
    source: str
    timestamp: str
    level: str
    message: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DashboardPanel:
    title: str
    visualization: str
    query: str
    value: str
    status: str


@dataclass(frozen=True)
class IntegrationSnapshot:
    service: str
    category: str
    status: str
    events: list[IntegrationEvent]
    dashboards: list[DashboardPanel]
    metrics: dict[str, Any]
    exported_logs: list[str]


INTEGRATIONS = {
    "github_actions": "CI/CD",
    "jenkins": "CI/CD",
    "docker": "Container",
    "kubernetes": "Orchestration",
    "grafana": "Monitoring",
    "prometheus": "Metrics",
}


def simulate_integration_report(seed: int | None = None) -> dict[str, Any]:
    rng = random.Random(seed)
    snapshots = [
        _simulate_github_actions(rng),
        _simulate_jenkins(rng),
        _simulate_docker(rng),
        _simulate_kubernetes(rng),
        _simulate_grafana(rng),
        _simulate_prometheus(rng),
    ]

    return {
        "generated_at": _now_iso(),
        "summary": _summarize(snapshots),
        "integrations": [snapshot.__dict__ for snapshot in snapshots],
    }


def _simulate_github_actions(rng: random.Random) -> IntegrationSnapshot:
    status = rng.choice(["healthy", "degraded"])
    events = [
        _event(
            "github_actions",
            "INFO",
            "Workflow aegisops-api-build completed",
            {"run_id": "8342991", "branch": "main", "duration_s": 412},
        ),
        _event(
            "github_actions",
            "WARN",
            "Unit tests flaky in job 'pytest'",
            {"failure_rate": "6%", "job": "pytest"},
        ),
    ]
    dashboards = [
        _panel("CI Throughput", "timeseries", "runs_per_day", "42", status),
        _panel("Build Success Rate", "gauge", "success_ratio", "93%", status),
    ]
    metrics = {"runs_last_24h": 42, "success_rate": 0.93, "avg_duration_s": 410}
    exported = _exported_logs("github_actions", events)
    return IntegrationSnapshot(
        service="GitHub Actions",
        category=INTEGRATIONS["github_actions"],
        status=status,
        events=events,
        dashboards=dashboards,
        metrics=metrics,
        exported_logs=exported,
    )


def _simulate_jenkins(rng: random.Random) -> IntegrationSnapshot:
    status = rng.choice(["healthy", "degraded"])
    events = [
        _event(
            "jenkins",
            "INFO",
            "Pipeline aegisops-deploy succeeded",
            {"job": "deploy-prod", "build": "#1842", "duration_s": 622},
        ),
        _event(
            "jenkins",
            "ERROR",
            "Artifact missing for stage 'publish'",
            {"job": "build-release", "build": "#1843"},
        ),
    ]
    dashboards = [
        _panel("Deploy Lead Time", "bar", "lead_time_minutes", "38m", status),
        _panel("Failure Rate", "gauge", "failure_ratio", "8%", status),
    ]
    metrics = {"deploys_last_24h": 11, "failure_rate": 0.08}
    exported = _exported_logs("jenkins", events)
    return IntegrationSnapshot(
        service="Jenkins",
        category=INTEGRATIONS["jenkins"],
        status=status,
        events=events,
        dashboards=dashboards,
        metrics=metrics,
        exported_logs=exported,
    )


def _simulate_docker(rng: random.Random) -> IntegrationSnapshot:
    status = rng.choice(["healthy", "degraded"])
    events = [
        _event(
            "docker",
            "INFO",
            "Image aegisops-api:2026.05.10 pushed",
            {"registry": "ghcr.io", "size_mb": 312},
        ),
        _event(
            "docker",
            "WARN",
            "Layer cache miss detected",
            {"layer": "pip install", "impact": "+2m build time"},
        ),
    ]
    dashboards = [
        _panel("Image Pull Latency", "timeseries", "pull_latency_ms", "320ms", status),
        _panel("Registry Storage", "gauge", "registry_usage", "68%", status),
    ]
    metrics = {"images_built": 7, "avg_pull_ms": 320}
    exported = _exported_logs("docker", events)
    return IntegrationSnapshot(
        service="Docker Registry",
        category=INTEGRATIONS["docker"],
        status=status,
        events=events,
        dashboards=dashboards,
        metrics=metrics,
        exported_logs=exported,
    )


def _simulate_kubernetes(rng: random.Random) -> IntegrationSnapshot:
    status = rng.choice(["healthy", "degraded"])
    events = [
        _event(
            "kubernetes",
            "WARN",
            "Pod aegisops-api-7d9d pending scheduling",
            {"reason": "Insufficient cpu", "namespace": "prod"},
        ),
        _event(
            "kubernetes",
            "INFO",
            "HPA scaled aegisops-api from 4 to 6",
            {"namespace": "prod"},
        ),
    ]
    dashboards = [
        _panel("Cluster CPU", "timeseries", "node_cpu_usage", "71%", status),
        _panel("Pod Restarts", "bar", "restart_count", "3", status),
    ]
    metrics = {"node_cpu_pct": 0.71, "pending_pods": 2}
    exported = _exported_logs("kubernetes", events)
    return IntegrationSnapshot(
        service="Kubernetes",
        category=INTEGRATIONS["kubernetes"],
        status=status,
        events=events,
        dashboards=dashboards,
        metrics=metrics,
        exported_logs=exported,
    )


def _simulate_grafana(rng: random.Random) -> IntegrationSnapshot:
    status = rng.choice(["healthy", "degraded"])
    events = [
        _event(
            "grafana",
            "INFO",
            "Dashboard 'AegisOps Core' refreshed",
            {"dashboard_id": "core-112", "panels": 18},
        ),
        _event(
            "grafana",
            "WARN",
            "Panel latency above threshold",
            {"panel": "API p95 latency", "value": "640ms"},
        ),
    ]
    dashboards = [
        _panel("API Latency p95", "timeseries", "http_p95_ms", "640ms", status),
        _panel("Error Rate", "gauge", "error_rate", "1.2%", status),
    ]
    metrics = {"dashboards": 12, "alerts": 3}
    exported = _exported_logs("grafana", events)
    return IntegrationSnapshot(
        service="Grafana",
        category=INTEGRATIONS["grafana"],
        status=status,
        events=events,
        dashboards=dashboards,
        metrics=metrics,
        exported_logs=exported,
    )


def _simulate_prometheus(rng: random.Random) -> IntegrationSnapshot:
    status = rng.choice(["healthy", "degraded"])
    events = [
        _event(
            "prometheus",
            "INFO",
            "Scrape cycle completed",
            {"targets": 64, "success_rate": "98%"},
        ),
        _event(
            "prometheus",
            "WARN",
            "High memory usage on prometheus-server",
            {"memory_pct": "82%"},
        ),
    ]
    dashboards = [
        _panel("Scrape Success", "gauge", "scrape_success", "98%", status),
        _panel("TSDB Size", "timeseries", "tsdb_size_gb", "42GB", status),
    ]
    metrics = {"scrape_success": 0.98, "tsdb_size_gb": 42}
    exported = _exported_logs("prometheus", events)
    return IntegrationSnapshot(
        service="Prometheus",
        category=INTEGRATIONS["prometheus"],
        status=status,
        events=events,
        dashboards=dashboards,
        metrics=metrics,
        exported_logs=exported,
    )


def _summarize(snapshots: list[IntegrationSnapshot]) -> dict[str, Any]:
    degraded = [snapshot.service for snapshot in snapshots if snapshot.status != "healthy"]
    return {
        "total_integrations": len(snapshots),
        "degraded": degraded,
        "status": "degraded" if degraded else "healthy",
    }


def _event(source: str, level: str, message: str, metadata: dict[str, Any]) -> IntegrationEvent:
    return IntegrationEvent(
        source=source,
        timestamp=_now_iso(),
        level=level,
        message=message,
        metadata=metadata,
    )


def _panel(title: str, visualization: str, query: str, value: str, status: str) -> DashboardPanel:
    return DashboardPanel(
        title=title,
        visualization=visualization,
        query=query,
        value=value,
        status=status,
    )


def _exported_logs(source: str, events: list[IntegrationEvent]) -> list[str]:
    lines: list[str] = []
    for event in events:
        lines.append(
            f"{event.timestamp} {event.level} {source}: {event.message} | {event.metadata}"
        )
    return lines


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

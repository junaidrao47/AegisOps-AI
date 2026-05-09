from __future__ import annotations

import concurrent.futures
import logging
from typing import Callable

from aegis_ai.agents.cicd.agent import analyze_cicd
from aegis_ai.agents.docs_retrieval.agent import retrieve_docs
from aegis_ai.agents.kubernetes.agent import analyze_kubernetes
from aegis_ai.agents.log_analysis.agent import analyze_logs
from aegis_ai.agents.remediation.agent import recommend_fixes
from aegis_ai.agents.security.agent import analyze_security
from aegis_ai.orchestration.router import route
from aegis_ai.orchestration.state import AgentResult, IncidentContext

logger = logging.getLogger(__name__)


AGENT_REGISTRY: dict[str, Callable[[IncidentContext], AgentResult]] = {
    "log_analysis": analyze_logs,
    "kubernetes": analyze_kubernetes,
    "cicd": analyze_cicd,
    "security": analyze_security,
    "docs_retrieval": retrieve_docs,
}


def build_graph():
    """Return a runnable orchestration pipeline."""

    def run(ctx: IncidentContext) -> IncidentContext:
        agents_to_run = route(ctx)
        _run_parallel_agents(ctx, agents_to_run)
        _merge_shared_context(ctx)
        recommend_fixes(ctx)
        return ctx

    return run


def _run_parallel_agents(ctx: IncidentContext, agent_names: list[str]) -> None:
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(agent_names) or 1) as executor:
        futures = {
            executor.submit(_run_agent, ctx, name): name
            for name in agent_names
            if name in AGENT_REGISTRY
        }
        for future in concurrent.futures.as_completed(futures):
            name = futures[future]
            try:
                result = future.result()
                ctx.agent_results[name] = result
            except Exception as exc:  # pragma: no cover - safety net
                ctx.errors.append(f"{name}: {exc}")
                logger.exception("Agent %s failed", name)


def _run_agent(ctx: IncidentContext, name: str) -> AgentResult:
    agent_fn = AGENT_REGISTRY[name]
    return agent_fn(ctx)


def _merge_shared_context(ctx: IncidentContext) -> None:
    combined_findings: list[str] = []
    combined_evidence: list[str] = []
    summaries: list[str] = []

    for result in ctx.agent_results.values():
        summaries.append(f"{result.agent}: {result.summary}")
        combined_findings.extend(result.findings)
        combined_evidence.extend(result.evidence)

    ctx.shared_context["summaries"] = summaries
    ctx.shared_context["findings"] = combined_findings
    ctx.shared_context["evidence"] = combined_evidence
    if summaries:
        ctx.summary = " | ".join(summaries)

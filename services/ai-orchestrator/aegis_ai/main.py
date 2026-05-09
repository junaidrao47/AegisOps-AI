from __future__ import annotations

import argparse
import json

from aegis_ai.orchestration.graph import build_graph
from aegis_ai.orchestration.state import IncidentContext


def _sample_incident_context() -> IncidentContext:
    payload = {
        "incident_type": "kubernetes",
        "summary": "API pods are crashing after deployment",
        "logs": [
            "Back-off restarting failed container",
            "Error: OOMKilled container",
            "ImagePullBackOff for aegisops-api:latest",
        ],
        "pipeline": "Build failed: unit tests failed in stage test",
        "tags": ["k8s", "cicd"],
        "rag_query": "kubernetes crashloopbackoff imagepullbackoff remediation",
    }
    return IncidentContext(incident_id="sample-incident-001", payload=payload)


def _serialize_result(ctx: IncidentContext) -> dict:
    return {
        "incident_id": ctx.incident_id,
        "summary": ctx.summary,
        "recommendations": ctx.recommendations,
        "agent_results": {
            key: {
                "summary": result.summary,
                "findings": result.findings,
                "confidence": result.confidence,
                "evidence": result.evidence,
            }
            for key, result in ctx.agent_results.items()
        },
        "errors": ctx.errors,
    }


def main() -> None:
    """Service entrypoint for running orchestration locally."""

    parser = argparse.ArgumentParser(description="AegisOps AI Orchestrator")
    parser.add_argument("--sample", action="store_true", help="Run a sample incident payload")
    args = parser.parse_args()

    graph = build_graph()
    if args.sample:
        ctx = _sample_incident_context()
        result = graph(ctx)
        print(json.dumps(_serialize_result(result), indent=2))
        return

    print("AegisOps AI Orchestrator is ready. Use --sample to run a smoke test.")


if __name__ == "__main__":
    main()

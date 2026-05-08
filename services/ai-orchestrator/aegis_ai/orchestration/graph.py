from aegis_ai.orchestration.state import IncidentContext


def build_graph():
    """Placeholder for LangGraph construction.

    Planned: route between agents (logs/k8s/cicd/security/docs/remediation).
    """

    def run(ctx: IncidentContext) -> IncidentContext:
        return ctx

    return run

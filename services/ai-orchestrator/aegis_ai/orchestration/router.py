from aegis_ai.orchestration.state import IncidentContext


def route(ctx: IncidentContext) -> str:
    """Simple router placeholder.

    Planned: use incident metadata to pick the next agent.
    """

    return "log_analysis"

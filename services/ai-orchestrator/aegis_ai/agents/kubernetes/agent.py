from aegis_ai.orchestration.state import IncidentContext


def analyze_kubernetes(ctx: IncidentContext) -> IncidentContext:
    ctx.summary = ctx.summary or "kubernetes analysis not implemented"
    return ctx

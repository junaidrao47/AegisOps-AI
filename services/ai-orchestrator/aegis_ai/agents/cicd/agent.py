from aegis_ai.orchestration.state import IncidentContext


def analyze_cicd(ctx: IncidentContext) -> IncidentContext:
    ctx.summary = ctx.summary or "cicd analysis not implemented"
    return ctx

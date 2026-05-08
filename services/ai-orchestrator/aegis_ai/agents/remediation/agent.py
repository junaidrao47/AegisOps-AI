from aegis_ai.orchestration.state import IncidentContext


def recommend_fixes(ctx: IncidentContext) -> IncidentContext:
    ctx.recommendations = ctx.recommendations or ["remediation not implemented"]
    return ctx

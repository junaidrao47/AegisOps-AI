from aegis_ai.orchestration.state import IncidentContext


def analyze_security(ctx: IncidentContext) -> IncidentContext:
    ctx.summary = ctx.summary or "security analysis not implemented"
    return ctx

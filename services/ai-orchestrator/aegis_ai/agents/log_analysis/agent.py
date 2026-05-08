from aegis_ai.orchestration.state import IncidentContext


def analyze_logs(ctx: IncidentContext) -> IncidentContext:
    ctx.summary = ctx.summary or "log analysis not implemented"
    return ctx

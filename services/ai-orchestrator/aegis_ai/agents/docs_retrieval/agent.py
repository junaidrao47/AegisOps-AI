from aegis_ai.orchestration.state import IncidentContext


def retrieve_docs(ctx: IncidentContext) -> IncidentContext:
    ctx.summary = ctx.summary or "docs retrieval not implemented"
    return ctx

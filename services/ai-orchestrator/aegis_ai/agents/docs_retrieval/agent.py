from __future__ import annotations

from aegis_ai.orchestration.state import AgentResult, IncidentContext


def retrieve_docs(ctx: IncidentContext) -> AgentResult:
    query = ctx.payload.get("rag_query") or ctx.summary or ctx.payload.get("query") or ""
    results: list[dict] = []
    summary = "docs retrieval skipped"
    confidence = 0.3

    if query:
        try:
            from aegis_ai.rag.pipeline import retrieve_context

            results = retrieve_context(query, top_k=5)
            summary = "docs retrieval complete" if results else "no docs matched"
            confidence = 0.6 if results else 0.4
            ctx.payload["rag_results"] = results
            ctx.payload["rag_context"] = _format_context(results)
        except Exception as exc:  # pragma: no cover - optional dependency
            ctx.errors.append(f"docs_retrieval: {exc}")
            summary = "docs retrieval failed"

    evidence = [item.get("metadata", {}).get("source", "unknown") for item in results]
    findings = [f"Doc match: {item.get('metadata', {}).get('source', 'unknown')}" for item in results]

    return AgentResult(
        agent="docs_retrieval",
        summary=summary,
        findings=findings,
        confidence=confidence,
        evidence=evidence,
        metadata={"query": query},
    )


def _format_context(results: list[dict]) -> str:
    blocks: list[str] = []
    for result in results:
        source = result.get("metadata", {}).get("source", "unknown")
        text = result.get("text", "").strip()
        if text:
            blocks.append(f"Source: {source}\n{text}")
    return "\n\n".join(blocks)

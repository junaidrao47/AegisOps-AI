# AegisOps AI Orchestrator

This service hosts the multi-agent orchestration layer (LangGraph) and the RAG pipeline used to diagnose incidents and recommend remediation.

## Structure
- `aegis_ai/orchestration`: graph/state/router glue
- `aegis_ai/agents`: individual agents (logs, k8s, cicd, security, docs, remediation)
- `aegis_ai/rag`: embeddings, vectorstore integration, retrieval pipeline
- `aegis_ai/integrations`: Groq + Chroma integration shims

HELLO1HELLO1HELLO1HELLO1HELLO1
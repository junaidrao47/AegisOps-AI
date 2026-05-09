# AegisOps AI

AegisOps AI is an enterprise DevOps intelligence platform that combines a Next.js frontend, a FastAPI gateway, a LangGraph orchestration layer, and a RAG pipeline for incident analysis, remediation guidance, and operational knowledge retrieval.

## Architecture

```mermaid
flowchart LR
	U[Platform Engineer / SRE]

	subgraph FE[Frontend Layer]
		WEB[Next.js 15 App\nDashboard, incidents, logs, orchestrator, auth]
	end

	subgraph API[Backend Layer]
		GW[FastAPI API Gateway\nAuth, incidents, uploads, orchestration]
		ORCH[LangGraph Orchestrator\nRouting + agent coordination]
		WORKERS[Background Workers / Celery]
	end

	subgraph DATA[Data Layer]
		PG[(PostgreSQL\nUsers, incidents, sessions, timelines)]
		REDIS[(Redis\nCache, sessions, queues)]
		CHROMA[(ChromaDB Vector Store\nChunks, embeddings, retrieval)]
	end

	subgraph AI[AI / RAG Layer]
		RAG[RAG Pipeline\nIngest, chunk, embed, retrieve]
		EMB[Sentence Transformers\nEmbeddings]
		LLM[Groq LLMs\nReasoning + synthesis]
		AGENTS[Specialized Agents\nLog, Kubernetes, CI/CD, security, remediation]
	end

	DOCS[(Operational docs\nRunbooks, postmortems, SOPs)]
	LOGS[(Logs / incident evidence)]

	U --> WEB
	WEB --> GW

	GW --> PG
	GW --> REDIS
	GW --> ORCH
	GW --> WORKERS

	ORCH --> AGENTS
	ORCH --> RAG
	ORCH --> LLM

	WORKERS --> RAG
	WORKERS --> CHROMA

	DOCS --> RAG
	LOGS --> RAG
	RAG --> EMB
	EMB --> CHROMA
	CHROMA --> RAG
	RAG --> LLM

	REDIS <--> WORKERS
	PG <--> GW
	REDIS <--> GW

	classDef frontend fill:#0f172a,stroke:#67e8f9,stroke-width:1px,color:#e2e8f0;
	classDef backend fill:#111827,stroke:#22d3ee,stroke-width:1px,color:#e2e8f0;
	classDef data fill:#0b1220,stroke:#38bdf8,stroke-width:1px,color:#e2e8f0;
	classDef ai fill:#111827,stroke:#2dd4bf,stroke-width:1px,color:#e2e8f0;

	class WEB frontend;
	class GW,ORCH,WORKERS backend;
	class PG,REDIS,CHROMA data;
	class RAG,EMB,LLM,AGENTS ai;
```

## What the flow looks like

1. The user interacts with the Next.js frontend.
2. The frontend calls the FastAPI gateway for auth, incidents, logs, and orchestrator analysis.
3. PostgreSQL stores durable application data such as users, incident records, sessions, and timelines.
4. Redis handles fast-changing state such as queues, caching, session helpers, and worker coordination.
5. The orchestrator routes incident context into the RAG pipeline and specialized agents.
6. Operational documents and logs are embedded into ChromaDB, then retrieved back as context for Groq-based reasoning.
7. The final output is synthesized into recommendations, findings, and remediation guidance for the operator.

## Main Components

- Frontend: Next.js 15, TypeScript, TailwindCSS, shadcn/ui-style primitives, Framer Motion, Zustand, React Query, Monaco Editor, and Recharts.
- Backend: FastAPI, Pydantic, SQLAlchemy, Uvicorn, Celery, and Redis.
- AI: LangGraph, LangChain-style orchestration, ChromaDB, Sentence Transformers, and Groq LLMs.

## Key surfaces

- [frontend/](frontend/) contains the operator dashboard and architecture page.
- [services/api-gateway/](services/api-gateway/) contains the FastAPI gateway and persistence layer.
- [services/ai-orchestrator/](services/ai-orchestrator/) contains the multi-agent RAG and reasoning system.

## Architecture page

The rendered architecture view is available at /architecture in the frontend app.

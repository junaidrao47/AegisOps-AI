import { AppShell } from '@/components/app-shell';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

const layers = [
  {
    title: 'Frontend',
    description: 'Next.js 15 dashboard with auth, incidents, logs, and orchestrator workflows.',
    accent: 'border-cyan-400/20 bg-cyan-400/5',
  },
  {
    title: 'Gateway',
    description: 'FastAPI entrypoint for auth, persistence, uploads, orchestration, and analysis.',
    accent: 'border-sky-400/20 bg-sky-400/5',
  },
  {
    title: 'State',
    description: 'PostgreSQL for durable records and Redis for cache, queues, and session helpers.',
    accent: 'border-blue-400/20 bg-blue-400/5',
  },
  {
    title: 'AI + RAG',
    description: 'LangGraph agents, retrieval pipeline, ChromaDB vectors, embeddings, and Groq LLMs.',
    accent: 'border-emerald-400/20 bg-emerald-400/5',
  },
];

const flowSteps = [
  'User interacts with the Next.js UI for auth, incidents, logs, and analysis.',
  'The API gateway validates requests and stores durable data in PostgreSQL while Redis handles queues and session coordination.',
  'Log and document inputs are normalized by the RAG pipeline, embedded, and written to ChromaDB.',
  'The orchestrator routes context into specialized agents and Groq LLM reasoning.',
  'The synthesized response returns as findings, recommendations, and remediation guidance.',
];

const diagramEdges = [
  'Frontend',
  'API Gateway',
  'PostgreSQL',
  'Redis',
  'RAG Pipeline',
  'ChromaDB',
  'Orchestrator',
  'Specialized Agents',
  'Groq LLMs',
];

export default function ArchitecturePage() {
  return (
    <AppShell
      title="Architecture"
      description="A layered view of the frontend, backend, state, and AI systems that power AegisOps AI."
    >
      <div className="space-y-6">
        <section className="relative overflow-hidden rounded-[2rem] border border-white/10 bg-white/5 p-6 shadow-glow backdrop-blur md:p-8">
          <div className="absolute inset-0 bg-grid opacity-20" />
          <div className="relative space-y-4">
            <Badge className="border-cyan-400/20 bg-cyan-400/10 text-cyan-200">System architecture</Badge>
            <div className="space-y-3">
              <h1 className="text-3xl font-semibold tracking-tight text-white md:text-5xl">
                Frontend, backend, state, and RAG in one operating model.
              </h1>
              <p className="max-w-3xl text-sm leading-7 text-slate-300 md:text-base">
                This page shows how the UI, API gateway, databases, Redis, and AI orchestration layer
                fit together to analyze incidents and deliver remediation guidance.
              </p>
            </div>
          </div>
        </section>

        <section className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
          <Card className="border-white/10 bg-white/5 text-white">
            <CardHeader>
              <CardTitle>Architecture diagram</CardTitle>
              <CardDescription className="text-slate-300">
                The board below shows the main runtime path, storage layer, and AI reasoning chain.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="rounded-[2rem] border border-white/10 bg-black/20 p-5">
                <div className="grid gap-4 lg:grid-cols-[1fr_auto_1fr_auto_1fr] lg:items-center">
                  <div className="rounded-3xl border border-cyan-400/20 bg-cyan-400/10 p-4 text-center">
                    <p className="text-xs uppercase tracking-[0.3em] text-cyan-200">Frontend</p>
                    <p className="mt-2 text-sm font-medium text-white">Next.js 15 UI</p>
                    <p className="mt-1 text-xs text-slate-300">Dashboard, auth, logs, incidents</p>
                  </div>
                  <div className="flex justify-center text-cyan-300">
                    <span className="rounded-full border border-cyan-400/20 bg-cyan-400/10 px-3 py-2 text-xs">API flow</span>
                  </div>
                  <div className="rounded-3xl border border-sky-400/20 bg-sky-400/10 p-4 text-center">
                    <p className="text-xs uppercase tracking-[0.3em] text-sky-200">Gateway</p>
                    <p className="mt-2 text-sm font-medium text-white">FastAPI API Gateway</p>
                    <p className="mt-1 text-xs text-slate-300">Auth, orchestration, persistence</p>
                  </div>
                  <div className="flex justify-center text-sky-300">
                    <span className="rounded-full border border-sky-400/20 bg-sky-400/10 px-3 py-2 text-xs">Analysis</span>
                  </div>
                  <div className="rounded-3xl border border-emerald-400/20 bg-emerald-400/10 p-4 text-center">
                    <p className="text-xs uppercase tracking-[0.3em] text-emerald-200">Orchestrator</p>
                    <p className="mt-2 text-sm font-medium text-white">LangGraph routing</p>
                    <p className="mt-1 text-xs text-slate-300">Agents, retrieval, synthesis</p>
                  </div>
                </div>

                <div className="my-5 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                  <div className="rounded-3xl border border-white/10 bg-white/5 p-4">
                    <p className="text-xs uppercase tracking-[0.3em] text-slate-400">PostgreSQL</p>
                    <p className="mt-2 text-sm font-medium text-white">Durable records</p>
                    <p className="mt-1 text-xs text-slate-400">Users, incidents, sessions, timelines</p>
                  </div>
                  <div className="rounded-3xl border border-white/10 bg-white/5 p-4">
                    <p className="text-xs uppercase tracking-[0.3em] text-slate-400">Redis</p>
                    <p className="mt-2 text-sm font-medium text-white">Queues + cache</p>
                    <p className="mt-1 text-xs text-slate-400">Session helpers, workers, fast state</p>
                  </div>
                  <div className="rounded-3xl border border-white/10 bg-white/5 p-4">
                    <p className="text-xs uppercase tracking-[0.3em] text-slate-400">RAG Pipeline</p>
                    <p className="mt-2 text-sm font-medium text-white">Chunk + embed + retrieve</p>
                    <p className="mt-1 text-xs text-slate-400">Docs and logs turned into context</p>
                  </div>
                  <div className="rounded-3xl border border-white/10 bg-white/5 p-4">
                    <p className="text-xs uppercase tracking-[0.3em] text-slate-400">ChromaDB</p>
                    <p className="mt-2 text-sm font-medium text-white">Vector store</p>
                    <p className="mt-1 text-xs text-slate-400">Semantic retrieval for operational knowledge</p>
                  </div>
                </div>

                <div className="grid gap-4 lg:grid-cols-[1fr_auto_1fr_auto_1fr] lg:items-center">
                  <div className="rounded-3xl border border-white/10 bg-white/5 p-4 text-center">
                    <p className="text-xs uppercase tracking-[0.3em] text-slate-400">Logs + Docs</p>
                    <p className="mt-2 text-sm font-medium text-white">Incident evidence</p>
                    <p className="mt-1 text-xs text-slate-400">Runbooks, postmortems, raw logs</p>
                  </div>
                  <div className="flex justify-center text-slate-500">
                    <span className="text-xs">→</span>
                  </div>
                  <div className="rounded-3xl border border-cyan-400/20 bg-cyan-400/5 p-4 text-center">
                    <p className="text-xs uppercase tracking-[0.3em] text-cyan-200">RAG pipeline</p>
                    <p className="mt-2 text-sm font-medium text-white">Operational retrieval</p>
                    <p className="mt-1 text-xs text-slate-400">Uses embeddings from docs and logs</p>
                  </div>
                  <div className="flex justify-center text-slate-500">
                    <span className="text-xs">→</span>
                  </div>
                  <div className="rounded-3xl border border-emerald-400/20 bg-emerald-400/5 p-4 text-center">
                    <p className="text-xs uppercase tracking-[0.3em] text-emerald-200">AI output</p>
                    <p className="mt-2 text-sm font-medium text-white">Agents + Groq LLMs</p>
                    <p className="mt-1 text-xs text-slate-400">Findings, remediation, summaries</p>
                  </div>
                </div>
              </div>

              <div className="rounded-3xl border border-cyan-400/20 bg-cyan-400/5 p-5">
                <p className="text-sm font-medium text-cyan-100">How it runs</p>
                <ol className="mt-3 space-y-3 text-sm leading-6 text-slate-200">
                  {flowSteps.map((flow, index) => (
                    <li key={flow} className="flex gap-3">
                      <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-cyan-300/30 bg-cyan-300/10 text-xs text-cyan-100">
                        {index + 1}
                      </span>
                      <span>{flow}</span>
                    </li>
                  ))}
                </ol>
              </div>
            </CardContent>
          </Card>

          <Card className="border-white/10 bg-white/5 text-white">
            <CardHeader>
              <CardTitle>What each layer owns</CardTitle>
              <CardDescription className="text-slate-300">
                Each tier has a clear responsibility so the system stays maintainable and scalable.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4 text-sm text-slate-300">
              <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
                <p className="font-medium text-white">Frontend</p>
                <p className="mt-1">Presents operator workflows and captures incident inputs, log payloads, and analysis requests.</p>
              </div>
              <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
                <p className="font-medium text-white">Backend</p>
                <p className="mt-1">Validates, persists, and orchestrates requests while coordinating background processing.</p>
              </div>
              <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
                <p className="font-medium text-white">Data</p>
                <p className="mt-1">Stores durable application state in PostgreSQL and uses Redis for fast coordination and queues.</p>
              </div>
              <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
                <p className="font-medium text-white">RAG + AI</p>
                <p className="mt-1">Embeds documents and logs, retrieves relevant context, and synthesizes agent output into recommendations.</p>
              </div>
            </CardContent>
          </Card>
        </section>

        <section className="grid gap-4 lg:grid-cols-2 xl:grid-cols-4">
          {layers.map((layer) => (
            <Card key={layer.title} className={`border-white/10 text-white ${layer.accent}`}>
              <CardHeader>
                <CardTitle className="text-lg">{layer.title}</CardTitle>
                <CardDescription className="text-slate-300">{layer.description}</CardDescription>
              </CardHeader>
            </Card>
          ))}
        </section>
      </div>
    </AppShell>
  );
}
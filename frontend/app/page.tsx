import Link from 'next/link';
import { ArrowRight, ShieldCheck, Activity, FileSearch, Workflow } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

const highlights = [
  {
    icon: Activity,
    title: 'Live incident command center',
    description: 'Monitor incidents, logs, and AI recommendations from one surface.',
  },
  {
    icon: FileSearch,
    title: 'RAG knowledge engine',
    description: 'Search operational docs and retrieved context with semantic embeddings.',
  },
  {
    icon: Workflow,
    title: 'Multi-agent analysis',
    description: 'Route work to log, Kubernetes, CI/CD, security, and remediation agents.',
  },
  {
    icon: ShieldCheck,
    title: 'Enterprise-grade controls',
    description: 'JWT auth, refresh sessions, uploads, timelines, and secure analysis flows.',
  },
];

export default function HomePage() {
  return (
    <main className="mx-auto min-h-screen max-w-7xl px-6 py-10 lg:px-10">
      <section className="relative overflow-hidden rounded-[2rem] border border-white/10 bg-white/5 p-8 shadow-glow backdrop-blur xl:p-12">
        <div className="absolute inset-0 bg-grid opacity-40" />
        <div className="relative flex flex-col gap-10 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-3xl space-y-6">
            <Badge className="border-cyan-400/30 bg-cyan-400/10 text-cyan-200 hover:bg-cyan-400/10">
              AegisOps AI Frontend
            </Badge>
            <div className="space-y-4">
              <h1 className="text-4xl font-semibold tracking-tight text-white md:text-6xl">
                DevOps intelligence that looks and feels premium.
              </h1>
              <p className="max-w-2xl text-base leading-7 text-slate-300 md:text-lg">
                This Next.js 15 app is wired for the API gateway: auth, incidents, log ingestion,
                and orchestrator analysis. It is built to present a real enterprise workflow, not a
                demo shell.
              </p>
            </div>
            <div className="flex flex-wrap gap-3">
              <Button asChild size="lg" className="bg-cyan-400 text-slate-950 hover:bg-cyan-300">
                <Link href="/dashboard">
                  Open dashboard <ArrowRight className="ml-2 h-4 w-4" />
                </Link>
              </Button>
              <Button asChild size="lg" variant="outline" className="border-white/15 bg-white/5 text-white hover:bg-white/10">
                <Link href="/orchestrator">Run orchestrator</Link>
              </Button>
              <Button asChild size="lg" variant="ghost" className="text-cyan-100 hover:bg-cyan-400/10 hover:text-cyan-50">
                <Link href="/architecture">View architecture</Link>
              </Button>
            </div>
          </div>
          <div className="grid w-full max-w-xl gap-4 sm:grid-cols-2">
            {highlights.map((item) => (
              <Card key={item.title} className="border-white/10 bg-slate-950/60 text-white">
                <CardHeader>
                  <item.icon className="h-6 w-6 text-cyan-300" />
                  <CardTitle className="mt-4 text-lg">{item.title}</CardTitle>
                  <CardDescription className="text-slate-300">{item.description}</CardDescription>
                </CardHeader>
              </Card>
            ))}
          </div>
        </div>
      </section>

      <section className="mt-10 grid gap-6 lg:grid-cols-3">
        <Card className="border-white/10 bg-white/5 text-white lg:col-span-2">
          <CardHeader>
            <CardTitle>Ready for the backend</CardTitle>
            <CardDescription className="text-slate-300">
              The API client is designed to hit the FastAPI gateway endpoints directly, with token
              storage, incident flows, and orchestrator analysis all separated cleanly.
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-3 text-sm text-slate-300 md:grid-cols-2">
            <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
              `GET /api/v1/health`
            </div>
            <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
              `POST /api/v1/auth/login`
            </div>
            <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
              `POST /api/v1/incidents`
            </div>
            <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
              `POST /api/v1/orchestrator/analyze`
            </div>
          </CardContent>
        </Card>

        <Card className="border-cyan-400/20 bg-cyan-400/5 text-white">
          <CardHeader>
            <CardTitle>Stack included</CardTitle>
            <CardDescription className="text-slate-300">
              Next.js 15, TypeScript, TailwindCSS, shadcn/ui-ready primitives, Framer Motion,
              Zustand, React Query, Monaco Editor, and Recharts.
            </CardDescription>
          </CardHeader>
        </Card>
      </section>

      <section className="mt-6 grid gap-6 lg:grid-cols-[0.9fr_1.1fr]">
        <Card className="border-white/10 bg-white/5 text-white">
          <CardHeader>
            <CardTitle>Architecture quick view</CardTitle>
            <CardDescription className="text-slate-300">
              A compact map of the main runtime path from operator to AI reasoning.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm text-slate-300">
            <div className="rounded-2xl border border-white/10 bg-black/20 p-4">Frontend → Gateway → PostgreSQL / Redis</div>
            <div className="rounded-2xl border border-white/10 bg-black/20 p-4">Logs + Docs → RAG pipeline → ChromaDB</div>
            <div className="rounded-2xl border border-white/10 bg-black/20 p-4">Orchestrator → Agents → Groq synthesis</div>
          </CardContent>
        </Card>

        <Card className="border-white/10 bg-white/5 text-white">
          <CardHeader>
            <CardTitle>What the architecture page shows</CardTitle>
            <CardDescription className="text-slate-300">
              It breaks the platform into UI, backend, state, and AI layers with the data flow between them.
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-3 md:grid-cols-2 text-sm text-slate-300">
            <div className="rounded-2xl border border-white/10 bg-black/20 p-4">Auth and session handling</div>
            <div className="rounded-2xl border border-white/10 bg-black/20 p-4">Incident persistence and timelines</div>
            <div className="rounded-2xl border border-white/10 bg-black/20 p-4">Redis queues and cache coordination</div>
            <div className="rounded-2xl border border-white/10 bg-black/20 p-4">RAG retrieval and agent synthesis</div>
          </CardContent>
        </Card>
      </section>
    </main>
  );
}

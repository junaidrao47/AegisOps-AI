'use client';

import { useQuery } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { AlertCircle, ShieldCheck, Server, Sparkles } from 'lucide-react';

import { AppShell } from '@/components/app-shell';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { OpsChart } from '@/components/dashboard/ops-chart';
import { api } from '@/lib/api';
import { useSessionStore } from '@/stores/use-session-store';

const metrics = [
  { label: 'Pipeline health', value: '94%', hint: 'Build + deploy success over last 24h' },
  { label: 'Incident MTTR', value: '22m', hint: 'Shorter because of AI routing' },
  { label: 'Docs recall', value: '87%', hint: 'RAG context hit rate' },
  { label: 'Auto-analysis', value: 'On', hint: 'Log upload triggers orchestrator' },
];

export default function DashboardPage() {
  const accessToken = useSessionStore((state) => state.accessToken);
  const healthQuery = useQuery({ queryKey: ['health'], queryFn: api.health });
  const incidentsQuery = useQuery({ queryKey: ['incidents'], queryFn: api.listIncidents, enabled: Boolean(accessToken) });

  return (
    <AppShell
      title="Command Center"
      description="Real-time visibility for incidents, analysis, uploads, and AI recommendations."
    >
      <div className="space-y-6">
        <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {metrics.map((metric) => (
            <motion.div key={metric.label} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
              <Card className="border-white/10 bg-white/5 text-white">
                <CardHeader>
                  <CardDescription>{metric.label}</CardDescription>
                  <CardTitle className="text-3xl">{metric.value}</CardTitle>
                  <p className="text-sm text-slate-400">{metric.hint}</p>
                </CardHeader>
              </Card>
            </motion.div>
          ))}
        </section>

        <section className="grid gap-6 xl:grid-cols-[1.4fr_0.6fr]">
          <OpsChart />
          <Card className="border-white/10 bg-white/5 text-white">
            <CardHeader>
              <Badge className="w-fit border-emerald-400/20 bg-emerald-400/10 text-emerald-200">
                Gateway status
              </Badge>
              <CardTitle className="flex items-center gap-2 text-xl">
                <Server className="h-5 w-5 text-cyan-300" />
                API Gateway
              </CardTitle>
              <CardDescription>
                {healthQuery.data ? `Backend is ${healthQuery.data.status}.` : 'Checking backend status...'}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4 text-sm text-slate-300">
              <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
                <p className="text-slate-400">Auth token</p>
                <p className="mt-1 font-medium text-white">{accessToken ? 'Session connected' : 'No token stored'}</p>
              </div>
              <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
                <p className="text-slate-400">Incidents loaded</p>
                <p className="mt-1 font-medium text-white">{incidentsQuery.data?.length ?? 0}</p>
              </div>
              <div className="flex items-center gap-2 text-cyan-200">
                <ShieldCheck className="h-4 w-4" />
                JWT + refresh session flow ready
              </div>
            </CardContent>
          </Card>
        </section>

        <section id="metrics" className="grid gap-6 lg:grid-cols-2">
          <Card className="border-white/10 bg-white/5 text-white">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-xl">
                <Sparkles className="h-5 w-5 text-cyan-300" />
                Recent incidents
              </CardTitle>
              <CardDescription>Fetched from the API gateway and scoped to the active session.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {incidentsQuery.data?.length ? (
                incidentsQuery.data.slice(0, 5).map((incident) => (
                  <div key={incident.id} className="rounded-2xl border border-white/10 bg-black/20 p-4">
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <p className="font-medium text-white">{incident.title}</p>
                        <p className="text-sm text-slate-400">{incident.environment} · {incident.severity}</p>
                      </div>
                      <Badge className="border-white/10 bg-white/5">#{incident.id}</Badge>
                    </div>
                  </div>
                ))
              ) : (
                <div className="rounded-2xl border border-dashed border-white/10 bg-black/10 p-6 text-sm text-slate-400">
                  {accessToken ? 'No incidents yet. Create one from the Incidents page.' : 'Log in to see your incidents.'}
                </div>
              )}
            </CardContent>
          </Card>

          <Card className="border-orange-400/20 bg-orange-400/5 text-white">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-xl">
                <AlertCircle className="h-5 w-5 text-orange-300" />
                Operational note
              </CardTitle>
              <CardDescription className="text-slate-300">
                Log uploads automatically create AI events and can trigger orchestrator analysis when enabled.
              </CardDescription>
            </CardHeader>
          </Card>
        </section>
      </div>
    </AppShell>
  );
}

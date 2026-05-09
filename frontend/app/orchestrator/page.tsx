'use client';

import { useState } from 'react';
import dynamic from 'next/dynamic';
import { useMutation, useQuery } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { BrainCircuit, Terminal } from 'lucide-react';

import { AppShell } from '@/components/app-shell';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { api } from '@/lib/api';
import type { OrchestratorAnalyzeResponse } from '@/lib/types';
import { useSessionStore } from '@/stores/use-session-store';

const MonacoEditor = dynamic(() => import('@monaco-editor/react'), { ssr: false });

export default function OrchestratorPage() {
  const accessToken = useSessionStore((state) => state.accessToken);
  const activeIncidentId = useSessionStore((state) => state.activeIncidentId);
  const [incidentType, setIncidentType] = useState('kubernetes');
  const [summary, setSummary] = useState('API pods are crashing after a deployment');
  const [ragQuery, setRagQuery] = useState('kubernetes crashloopbackoff imagepullbackoff remediation');
  const [tags, setTags] = useState('k8s,cicd');
  const [logText, setLogText] = useState('Back-off restarting failed container\nError: OOMKilled container\nImagePullBackOff for aegisops-api:latest');
  const [result, setResult] = useState<OrchestratorAnalyzeResponse | null>(null);
  const orchestratorHealthQuery = useQuery({
    queryKey: ['orchestrator-health'],
    queryFn: api.orchestratorHealth,
    enabled: Boolean(accessToken),
    retry: false,
  });

  const analyzeMutation = useMutation({
    mutationFn: () =>
      api.analyzeOrchestrator({
        incident_type: incidentType,
        summary,
        rag_query: ragQuery,
        tags: tags.split(',').map((value) => value.trim()).filter(Boolean),
        log_text: logText,
      }),
    onSuccess: (data) => setResult(data),
  });

  return (
    <AppShell
      title="Orchestrator"
      description="Route incidents into specialized reasoning agents and synthesize fix recommendations."
    >
      <div className="grid gap-6 xl:grid-cols-[1fr_0.9fr]">
        <Card className="border-white/10 bg-white/5 text-white">
          <CardHeader>
            <Badge className="w-fit border-cyan-400/20 bg-cyan-400/10 text-cyan-200">Premium analysis flow</Badge>
            <CardTitle className="flex items-center gap-2 text-xl">
              <BrainCircuit className="h-5 w-5 text-cyan-300" />
              Multi-agent input
            </CardTitle>
            <CardDescription>
              Feed the orchestrator incident context, logs, tags, and retrieval prompts.
            </CardDescription>
            {activeIncidentId ? (
              <div className="mt-2 rounded-2xl border border-white/10 bg-black/20 px-4 py-3 text-sm text-cyan-200">
                Connected incident #{activeIncidentId} from the incident creation flow.
              </div>
            ) : null}
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="incident-type">Incident type</Label>
                <Input id="incident-type" value={incidentType} onChange={(event) => setIncidentType(event.target.value)} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="tags">Tags</Label>
                <Input id="tags" value={tags} onChange={(event) => setTags(event.target.value)} />
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="summary">Summary</Label>
              <Input id="summary" value={summary} onChange={(event) => setSummary(event.target.value)} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="rag-query">RAG query</Label>
              <Input id="rag-query" value={ragQuery} onChange={(event) => setRagQuery(event.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>Logs / evidence</Label>
              <div className="overflow-hidden rounded-2xl border border-white/10 bg-black/20">
                <MonacoEditor
                  height="240px"
                  defaultLanguage="text"
                  value={logText}
                  onChange={(value) => setLogText(value ?? '')}
                  theme="vs-dark"
                  options={{ minimap: { enabled: false }, fontSize: 13, wordWrap: 'on' }}
                />
              </div>
            </div>
            <Button className="w-full" onClick={() => analyzeMutation.mutate()} disabled={analyzeMutation.isPending}>
              {analyzeMutation.isPending ? 'Analyzing...' : 'Run orchestrator'}
            </Button>
          </CardContent>
        </Card>

        <Card className="border-white/10 bg-white/5 text-white">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-xl">
              <Terminal className="h-5 w-5 text-cyan-300" />
              Output
            </CardTitle>
            <CardDescription>Results, agent findings, and remediation synthesis from the API gateway.</CardDescription>
            <div className="mt-2 rounded-2xl border border-white/10 bg-black/20 px-4 py-3 text-sm text-slate-300">
              {accessToken ? (
                orchestratorHealthQuery.data ? (
                  <span>
                    Orchestrator is {orchestratorHealthQuery.data.enabled ? 'enabled' : 'disabled'} and {orchestratorHealthQuery.data.available ? 'available' : 'unavailable'}.
                  </span>
                ) : (
                  <span>Checking orchestrator health...</span>
                )
              ) : (
                <span>Log in to verify orchestrator health.</span>
              )}
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {result ? (
              <>
                <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
                  <p className="text-sm text-slate-400">Summary</p>
                  <p className="mt-2 text-white">{result.summary ?? 'No summary returned.'}</p>
                </div>
                <div className="space-y-3">
                  <p className="text-sm font-medium text-slate-300">Agent results</p>
                  {Object.entries(result.agent_results).map(([name, agent]) => (
                    <motion.div key={name} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
                      <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
                        <div className="flex items-center justify-between gap-3">
                          <p className="font-medium text-white">{name}</p>
                          <Badge className="border-white/10 bg-white/5">{Math.round(agent.confidence * 100)}%</Badge>
                        </div>
                        <p className="mt-2 text-sm text-slate-300">{agent.summary}</p>
                        {agent.findings.length ? (
                          <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-slate-300">
                            {agent.findings.map((finding) => (
                              <li key={finding}>{finding}</li>
                            ))}
                          </ul>
                        ) : null}
                      </div>
                    </motion.div>
                  ))}
                </div>
                <div className="rounded-2xl border border-emerald-400/20 bg-emerald-400/5 p-4">
                  <p className="text-sm text-emerald-200">Recommendations</p>
                  <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-200">
                    {result.recommendations.map((recommendation) => (
                      <li key={recommendation}>{recommendation}</li>
                    ))}
                  </ul>
                </div>
              </>
            ) : (
              <div className="rounded-2xl border border-dashed border-white/10 bg-black/10 p-6 text-sm text-slate-400">
                Run the orchestrator to see parallel analysis results.
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </AppShell>
  );
}

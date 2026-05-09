'use client';

import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import { PlusCircle, Ticket } from 'lucide-react';

import { AppShell } from '@/components/app-shell';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { api } from '@/lib/api';
import { useSessionStore } from '@/stores/use-session-store';

export default function IncidentsPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const activeIncidentId = useSessionStore((state) => state.activeIncidentId);
  const setActiveIncidentId = useSessionStore((state) => state.setActiveIncidentId);
  const [title, setTitle] = useState('Checkout deployment degraded');
  const [description, setDescription] = useState('Pods started failing after the latest rollout.');
  const [severity, setSeverity] = useState('high');
  const [environment, setEnvironment] = useState('production');
  const [serviceName, setServiceName] = useState('api-gateway');
  const [deploymentVersion, setDeploymentVersion] = useState('v0.1.0');

  const incidentsQuery = useQuery({ queryKey: ['incidents'], queryFn: api.listIncidents });

  const createMutation = useMutation({
    mutationFn: () =>
      api.createIncident({
        title,
        description,
        severity,
        environment,
        service_name: serviceName,
        deployment_version: deploymentVersion,
      }),
    onSuccess: async (incident) => {
      setActiveIncidentId(incident.id);
      await queryClient.invalidateQueries({ queryKey: ['incidents'] });
      router.push('/orchestrator');
    },
  });

  return (
    <AppShell
      title="Incidents"
      description="Create and inspect incident records before attaching logs and orchestrator analysis."
    >
      <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
        <Card className="border-white/10 bg-white/5 text-white">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-xl">
              <PlusCircle className="h-5 w-5 text-cyan-300" />
              Create incident
            </CardTitle>
            <CardDescription>Matches the API gateway incident payload shape.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="title">Title</Label>
              <Input id="title" value={title} onChange={(event) => setTitle(event.target.value)} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="description">Description</Label>
              <Textarea id="description" value={description} onChange={(event) => setDescription(event.target.value)} />
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="severity">Severity</Label>
                <Input id="severity" value={severity} onChange={(event) => setSeverity(event.target.value)} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="environment">Environment</Label>
                <Input id="environment" value={environment} onChange={(event) => setEnvironment(event.target.value)} />
              </div>
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="service-name">Service name</Label>
                <Input id="service-name" value={serviceName} onChange={(event) => setServiceName(event.target.value)} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="deployment-version">Deployment version</Label>
                <Input id="deployment-version" value={deploymentVersion} onChange={(event) => setDeploymentVersion(event.target.value)} />
              </div>
            </div>
            <Button className="w-full" onClick={() => createMutation.mutate()} disabled={createMutation.isPending}>
              {createMutation.isPending ? 'Saving...' : 'Create incident'}
            </Button>
          </CardContent>
        </Card>

        <Card className="border-white/10 bg-white/5 text-white">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-xl">
              <Ticket className="h-5 w-5 text-cyan-300" />
              Recent incidents
            </CardTitle>
            <CardDescription>Fetched through React Query from `/api/v1/incidents`.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {activeIncidentId ? (
              <div className="rounded-2xl border border-cyan-400/20 bg-cyan-400/5 p-4 text-sm text-cyan-100">
                Active incident selected: #{activeIncidentId}. You can now move to logs or orchestrator analysis.
              </div>
            ) : null}
            {incidentsQuery.data?.length ? (
              incidentsQuery.data.map((incident) => (
                <div key={incident.id} className="rounded-2xl border border-white/10 bg-black/20 p-4">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="font-medium text-white">{incident.title}</p>
                      <p className="text-sm text-slate-400">{incident.service_name ?? 'service unknown'} · {incident.environment}</p>
                    </div>
                    <Badge className="border-white/10 bg-white/5">{incident.severity}</Badge>
                  </div>
                  {incident.description ? <p className="mt-3 text-sm text-slate-300">{incident.description}</p> : null}
                </div>
              ))
            ) : (
              <div className="rounded-2xl border border-dashed border-white/10 bg-black/10 p-6 text-sm text-slate-400">
                Create your first incident to see it here.
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </AppShell>
  );
}

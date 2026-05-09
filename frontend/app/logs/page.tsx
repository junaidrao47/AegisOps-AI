'use client';

import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { UploadCloud, Wrench } from 'lucide-react';

import { AppShell } from '@/components/app-shell';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Textarea } from '@/components/ui/textarea';
import { api } from '@/lib/api';

export default function LogsPage() {
  const [logText, setLogText] = useState('2024-01-15T10:30:00Z CrashLoopBackOff on pod aegisops-api\n2024-01-15T10:30:05Z OOMKilled container');
  const [incidentId, setIncidentId] = useState('1');
  const [file, setFile] = useState<File | null>(null);
  const [uploadResult, setUploadResult] = useState<string>('');
  const detectMutation = useMutation({
    mutationFn: () => api.detectLogSource(logText),
  });
  const uploadMutation = useMutation({
    mutationFn: async () => {
      if (!file) throw new Error('Choose a log file first');
      return api.uploadLogsBrief(Number(incidentId), file);
    },
    onSuccess: () => setUploadResult('Uploaded and processed exported logs.'),
  });

  return (
    <AppShell
      title="Logs"
      description="Detect source types, process exported logs, and route them into the AI workflow."
    >
      <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <Card className="border-white/10 bg-white/5 text-white">
          <CardHeader>
            <Badge className="w-fit border-cyan-400/20 bg-cyan-400/10 text-cyan-200">Log intelligence</Badge>
            <CardTitle className="flex items-center gap-2 text-xl">
              <Wrench className="h-5 w-5 text-cyan-300" />
              Detection and upload
            </CardTitle>
            <CardDescription>Paste logs or upload exported files from Docker, Kubernetes, Jenkins, or GitHub Actions.</CardDescription>
          </CardHeader>
          <CardContent>
            <Tabs defaultValue="paste">
              <TabsList className="mb-4">
                <TabsTrigger value="paste">Paste logs</TabsTrigger>
                <TabsTrigger value="upload">Upload file</TabsTrigger>
              </TabsList>

              <TabsContent value="paste" className="space-y-4">
                <Textarea value={logText} onChange={(event) => setLogText(event.target.value)} />
                <Button onClick={() => detectMutation.mutate()} disabled={detectMutation.isPending}>
                  {detectMutation.isPending ? 'Detecting...' : 'Detect source'}
                </Button>
                {detectMutation.data ? (
                  <div className="rounded-2xl border border-white/10 bg-black/20 p-4 text-sm text-slate-300">
                    <p className="text-white">Detected: {detectMutation.data.detected_source}</p>
                    <p>Confidence: {Math.round(detectMutation.data.confidence * 100)}%</p>
                    <pre className="mt-3 overflow-auto text-xs text-slate-400">{JSON.stringify(detectMutation.data.all_matches, null, 2)}</pre>
                  </div>
                ) : null}
              </TabsContent>

              <TabsContent value="upload" className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="incident-id">Incident ID</Label>
                  <Input id="incident-id" value={incidentId} onChange={(event) => setIncidentId(event.target.value)} />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="file">Exported log file</Label>
                  <Input id="file" type="file" onChange={(event) => setFile(event.target.files?.[0] ?? null)} />
                </div>
                <Button onClick={() => uploadMutation.mutate()} disabled={uploadMutation.isPending}>
                  <UploadCloud className="mr-2 h-4 w-4" />
                  {uploadMutation.isPending ? 'Uploading...' : 'Upload and process'}
                </Button>
                {uploadResult ? <p className="text-sm text-emerald-200">{uploadResult}</p> : null}
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>

        <Card className="border-white/10 bg-white/5 text-white">
          <CardHeader>
            <CardTitle>What happens next</CardTitle>
            <CardDescription>
              Uploaded logs can flow into the ingestion engine and auto-analysis hook for AI events.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm text-slate-300">
            <div className="rounded-2xl border border-white/10 bg-black/20 p-4">1. Parse and classify source</div>
            <div className="rounded-2xl border border-white/10 bg-black/20 p-4">2. Run chunking and findings detection</div>
            <div className="rounded-2xl border border-white/10 bg-black/20 p-4">3. Trigger orchestrator analysis when enabled</div>
          </CardContent>
        </Card>
      </div>
    </AppShell>
  );
}

import type {
  AuthRequest,
  IncidentCreateRequest,
  IncidentRead,
  LogIngestBriefResponse,
  LogIngestResponse,
  LogDetectSourceResponse,
  OrchestratorAnalyzeRequest,
  OrchestratorAnalyzeResponse,
  OrchestratorHealthResponse,
  TokenPair,
} from './types';
import { getAccessToken } from './auth';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? '/api/v1';

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  const token = getAccessToken();

  if (!headers.has('Content-Type') && !(init.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers,
    cache: 'no-store',
  });

  if (!response.ok) {
    const detail = await safeDetail(response);
    throw new Error(detail || `request_failed_${response.status}`);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

async function safeDetail(response: Response) {
  try {
    const data = await response.json();
    return typeof data?.detail === 'string' ? data.detail : JSON.stringify(data);
  } catch {
    return response.statusText;
  }
}

export const api = {
  health: () => request<{ status: string }>('/health'),
  orchestratorHealth: () => request<OrchestratorHealthResponse>('/orchestrator/health'),
  register: (payload: AuthRequest) => request<TokenPair>('/auth/register', { method: 'POST', body: JSON.stringify(payload) }),
  login: (payload: AuthRequest) => request<TokenPair>('/auth/login', { method: 'POST', body: JSON.stringify(payload) }),
  refresh: (refresh_token: string) => request<TokenPair>('/auth/refresh', { method: 'POST', body: JSON.stringify({ refresh_token }) }),
  logout: (everywhere = false) => request<{ detail: string }>('/auth/logout', { method: 'POST', body: JSON.stringify({ everywhere }) }),
  listIncidents: () => request<IncidentRead[]>('/incidents'),
  createIncident: (payload: IncidentCreateRequest) => request<IncidentRead>('/incidents', { method: 'POST', body: JSON.stringify(payload) }),
  analyzeOrchestrator: (payload: OrchestratorAnalyzeRequest) =>
    request<OrchestratorAnalyzeResponse>('/orchestrator/analyze', { method: 'POST', body: JSON.stringify(payload) }),
  detectLogSource: (log_text: string) =>
    request<LogDetectSourceResponse>('/logs/detect-source', { method: 'POST', body: JSON.stringify({ log_text }) }),
  processLogsBrief: (log_text: string, incident_id?: number) =>
    request<LogIngestBriefResponse>('/logs/process-brief', {
      method: 'POST',
      body: JSON.stringify({ log_text, incident_id }),
    }),
  uploadLogs: (incident_id: number, file: File) => {
    const formData = new FormData();
    formData.append('incident_id', String(incident_id));
    formData.append('file', file);
    return request<LogIngestResponse>('/logs/upload', { method: 'POST', body: formData });
  },
};

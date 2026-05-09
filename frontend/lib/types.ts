export type TokenPair = {
  access_token: string;
  refresh_token: string;
};

export type AuthRequest = {
  email?: string;
  password?: string;
  github_code?: string;
};

export type IncidentCreateRequest = {
  title: string;
  description?: string | null;
  severity?: string;
  environment?: string;
  service_name?: string | null;
  deployment_version?: string | null;
  started_at?: string | null;
  ended_at?: string | null;
};

export type IncidentRead = {
  id: number;
  title: string;
  description: string | null;
  severity: string;
  environment: string;
  service_name: string | null;
  deployment_version: string | null;
  started_at: string | null;
  ended_at: string | null;
  created_at: string;
  updated_at: string;
};

export type OrchestratorAnalyzeRequest = {
  incident_id?: number | null;
  log_text?: string | null;
  incident_type?: string | null;
  summary?: string | null;
  rag_query?: string | null;
  tags?: string[];
};

export type AgentResult = {
  summary: string;
  findings: string[];
  confidence: number;
  evidence: string[];
};

export type OrchestratorAnalyzeResponse = {
  incident_id: number | null;
  summary: string | null;
  recommendations: string[];
  agent_results: Record<string, AgentResult>;
  errors: string[];
};

export type LogDetectSourceResponse = {
  detected_source: string;
  confidence: number;
  all_matches: Record<string, number>;
};

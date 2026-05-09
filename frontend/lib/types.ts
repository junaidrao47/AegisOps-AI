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

export type OrchestratorHealthResponse = {
  enabled: boolean;
  available: boolean;
  path: string;
  auto_analyze_logs: boolean;
};

export type LogDetectSourceResponse = {
  detected_source: string;
  confidence: number;
  all_matches: Record<string, number>;
};

export type LogFindingSummary = {
  critical: number;
  high: number;
  medium: number;
  low: number;
  total: number;
};

export type LogFinding = {
  category: string;
  severity: string;
  title: string;
  evidence: string | null;
  source_type: string;
  confidence: number;
  timestamp: string | null;
};

export type LogIngestBriefResponse = {
  success: boolean;
  source_type: string;
  total_lines: number;
  parsed_lines: number;
  failed_lines: number;
  chunks_count: number;
  findings_count: number;
  findings_summary: LogFindingSummary;
  critical_findings: LogFinding[];
  high_findings: LogFinding[];
  processing_time_ms: number;
  message: string | null;
};

export type LogIngestResponse = {
  success: boolean;
  source_type: string;
  total_lines: number;
  parsed_lines: number;
  failed_lines: number;
  chunks_count: number;
  findings_count: number;
  findings_summary: LogFindingSummary;
  findings: LogFinding[];
  chunks: Array<{
    index: number;
    text: string;
    start_line: number;
    end_line: number;
    checksum: string;
  }>;
  processing_time_ms: number;
  metadata: {
    classification_confidence: number | null;
    classification_source: string | null;
    parser_source: string | null;
    parser_metadata: Record<string, unknown>;
    incident_id: number | null;
    attachment_id: number | null;
  };
};

# AI Orchestrator Integration Guide

This document describes the integration between the API Gateway and the AI Orchestrator services.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Integration Style](#integration-style)
- [API Endpoints](#api-endpoints)
- [Auto-Analysis Hooks](#auto-analysis-hooks)
- [Configuration](#configuration)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)

## Overview

The AegisOps platform integrates an AI-powered incident analysis system that automatically analyzes logs, detects issues, and provides remediation recommendations. The integration follows these design decisions:

1. **Python Library Integration**: The API Gateway calls the Orchestrator as a Python library (not over HTTP), providing faster, cheaper, and cleaner integration.

2. **Dual Integration Points**: 
   - API endpoints for explicit frontend-triggered analysis
   - Ingestion pipeline hooks for automatic AI analysis after log uploads

3. **Comprehensive Testing**: Both unit tests and Docker Compose integration tests ensure reliability.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        API Gateway                               │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                    REST API Routes                           ││
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      ││
│  │  │ /orchestrator│  │    /logs     │  │  /incidents  │      ││
│  │  │   /analyze   │  │   /upload    │  │              │      ││
│  │  └──────┬───────┘  └──────┬───────┘  └──────────────┘      ││
│  │         │                  │                                 ││
│  │  ┌──────▼──────────────────▼───────┐                        ││
│  │  │         Services Layer           │                        ││
│  │  │  ┌────────────────────────────┐  │                        ││
│  │  │  │    orchestrator.py         │  │                        ││
│  │  │  │  - run_orchestrator()      │  │                        ││
│  │  │  │  - run_orchestrator_async()│  │                        ││
│  │  │  │  - get_orchestrator_health()│ │                        ││
│  │  │  └────────────────────────────┘  │                        ││
│  │  │  ┌────────────────────────────┐  │                        ││
│  │  │  │    ingestion_service.py    │  │                        ││
│  │  │  │  - trigger_auto_analysis() │  │                        ││
│  │  │  └────────────────────────────┘  │                        ││
│  │  └──────────────────────────────────┘                        ││
│  │                                                                ││
│  │  ┌──────────────────────────────────────────────────────────┐││
│  │  │              Celery Workers (Async Tasks)                 ││
│  │  │  - run_orchestrator_analysis (background job)            ││
│  │  └──────────────────────────────────────────────────────────┘││
│  └─────────────────────────────────────────────────────────────┘│
│                            │                                      │
│                            │ Python import                        │
│                            ▼                                      │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                    AI Orchestrator                            ││
│  │  ┌─────────────────────────────────────────────────────────┐││
│  │  │              Orchestration Graph                         │││
│  │  │  ┌──────────┐  ┌──────────┐  ┌──────────┐              │││
│  │  │  │   Log    │  │   K8s    │  │   CI/CD  │              │││
│  │  │  │ Analysis │  │  Agent   │  │  Agent   │              │││
│  │  │  └──────────┘  └──────────┘  └──────────┘              │││
│  │  │  ┌──────────┐  ┌──────────┐  ┌──────────┐              │││
│  │  │  │ Security │  │  Docs    │  │Remediation│             │││
│  │  │  │  Agent   │  │Retrieval │  │  Agent   │              │││
│  │  │  └──────────┘  └──────────┘  └──────────┘              │││
│  │  └─────────────────────────────────────────────────────────┘││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

## Integration Style

### Python Library Integration (Choice 1B)

The API Gateway imports and calls the Orchestrator directly as a Python library:

```python
# services/api-gateway/app/services/orchestrator.py

def run_orchestrator(payload: dict[str, Any], incident_id: int | None = None) -> dict[str, Any]:
    """Run the AI orchestrator to analyze an incident."""
    if not settings.orchestrator_enabled:
        raise RuntimeError("orchestrator_disabled")

    _ensure_orchestrator_path()
    _import_orchestrator_modules()

    ctx = _orchestrator_modules["IncidentContext"](
        incident_id=str(incident_id or "unknown"),
        payload=payload
    )
    result = _orchestrator_modules["build_graph"]()(ctx)

    return {
        "incident_id": incident_id,
        "summary": result.summary,
        "recommendations": result.recommendations or [],
        "agent_results": {...},
        "errors": result.errors,
    }
```

**Benefits:**
- No network latency
- No serialization overhead
- Simpler error handling
- Easier debugging
- Lower infrastructure cost

## API Endpoints

### Orchestrator Endpoints

#### POST `/api/v1/orchestrator/analyze`

Run synchronous incident analysis.

**Request:**
```json
{
  "incident_id": 123,
  "log_text": "2024-01-15 ERROR: Pod crashing...",
  "incident_type": "kubernetes",
  "summary": "API pods are crashing",
  "tags": ["production", "critical"],
  "rag_query": "kubernetes crashloopbackoff remediation"
}
```

**Response:**
```json
{
  "incident_id": 123,
  "summary": "Pod crash detected due to OOM",
  "recommendations": [
    "Increase memory limits",
    "Check for memory leaks"
  ],
  "agent_results": {
    "log_analysis": {
      "summary": "OOMKilled detected",
      "findings": ["OOMKilled", "CrashLoopBackOff"],
      "confidence": 0.95,
      "evidence": ["Container my-app OOMKilled"]
    },
    "kubernetes": {
      "summary": "Kubernetes pod issue",
      "findings": ["Pod in CrashLoopBackOff"],
      "confidence": 0.9,
      "evidence": ["Pod status changed to CrashLoopBackOff"]
    }
  },
  "errors": []
}
```

#### POST `/api/v1/orchestrator/analyze-async`

Run asynchronous incident analysis (returns task ID for polling).

**Request:** Same as `/analyze`

**Response:**
```json
{
  "task_id": "abc123-def456",
  "status": "queued"
}
```

#### GET `/api/v1/orchestrator/health`

Get orchestrator health status.

**Response:**
```json
{
  "enabled": true,
  "available": true,
  "path": "/app/orchestrator",
  "auto_analyze_logs": true
}
```

## Auto-Analysis Hooks

### Ingestion Pipeline Integration (Choice 2C)

When logs are uploaded, the system automatically triggers AI analysis if enabled.

**Configuration:**
```bash
# .env
ORCHESTRATOR_AUTO_ANALYZE_LOGS=true
```

**Flow:**
1. User uploads log file via `/api/v1/logs/upload`
2. Log ingestion pipeline processes the file
3. If `ORCHESTRATOR_AUTO_ANALYZE_LOGS=true`, auto-analysis is triggered
4. AI results are stored as incident events
5. Response includes both ingestion and AI analysis results

**Code:**
```python
# services/api-gateway/app/api/v1/routes/log_ingestion.py

@router.post("/logs/upload", response_model=LogIngestResponse)
def upload_and_process_log(...):
    # ... process log file ...
    
    # Trigger auto-analysis hook
    if settings.orchestrator_auto_analyze_logs:
        ai_result = trigger_auto_analysis(
            raw_text,
            incident_id=incident.id,
            source_type=result.source_type.value,
        )
        if ai_result:
            _store_ai_event(db, incident.id, ai_result)
    
    db.commit()
    return _convert_pipeline_result(result)
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ORCHESTRATOR_ENABLED` | Enable/disable orchestrator | `true` |
| `ORCHESTRATOR_PATH` | Path to orchestrator module | `../ai-orchestrator` |
| `ORCHESTRATOR_AUTO_ANALYZE_LOGS` | Auto-analyze on log upload | `true` |

### Example `.env`

```bash
# API Gateway Configuration
ENVIRONMENT=production
DATABASE_URL=postgresql+psycopg://user:pass@postgres:5432/aegisops
REDIS_URL=redis://redis:6379/0

# Orchestrator Configuration
ORCHESTRATOR_ENABLED=true
ORCHESTRATOR_PATH=/app/orchestrator
ORCHESTRATOR_AUTO_ANALYZE_LOGS=true
```

## Testing

### Unit Tests

Run unit tests locally:

```bash
cd services/api-gateway
pip install -r requirements.txt
pytest tests/test_orchestrator.py -v
```

### Integration Tests with Docker Compose

Run full integration tests:

```bash
# Build and run tests
docker compose -f docker-compose.test.yml up --exit-code-from test

# View test results
docker compose -f docker-compose.test.yml logs test
```

### Test Coverage

The test suite covers:

1. **Orchestrator Service Tests**
   - Disabled orchestrator handling
   - Health check functionality
   - Module caching
   - Error handling

2. **Ingestion Service Tests**
   - Auto-analysis triggers
   - Async analysis
   - Disabled analysis handling

3. **Celery Task Tests**
   - Background job execution
   - Error handling

4. **Schema Tests**
   - Request/response validation
   - Default values

5. **Integration Tests**
   - API endpoint authentication
   - End-to-end workflows

## Troubleshooting

### Orchestrator Import Failed

**Error:** `RuntimeError: orchestrator_import_failed`

**Solutions:**
1. Verify `ORCHESTRATOR_PATH` points to correct directory
2. Check that `aegis_ai` package exists in the path
3. Ensure all orchestrator dependencies are installed

### Auto-Analysis Not Triggering

**Check:**
1. `ORCHESTRATOR_AUTO_ANALYZE_LOGS=true` in environment
2. `ORCHESTRATOR_ENABLED=true` in environment
3. Log text is not empty

### Health Check Failing

**Check:**
1. Orchestrator path exists and is accessible
2. Required dependencies are installed
3. No import errors in orchestrator module

### Debug Mode

Enable debug logging:

```bash
LOG_LEVEL=DEBUG
```

## Additional Resources

- [AI Orchestrator README](../../services/ai-orchestrator/README.md)
- [API Gateway README](../../services/api-gateway/README.md)
- [Main Project README](../../README.md)
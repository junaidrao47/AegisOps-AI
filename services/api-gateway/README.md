# AegisOps API Gateway (FastAPI)

This service is the main HTTP gateway for the AegisOps platform.

## Structure
- `app/main.py`: FastAPI app entrypoint
- `app/api/v1/routes`: versioned API routes
- `app/core`: configuration + security helpers
- `app/db`: SQLAlchemy session + models
- `app/workers`: Celery app + tasks (Redis)

## Next
- Add migrations (Alembic) and production-ready auth hardening
- Add incident ingestion endpoints (logs/docs upload)

## Auth (Module 1)
APIs (under `/api/v1/auth`):
- `POST /register`
- `POST /login`
- `POST /refresh`
- `POST /logout` (supports `{"everywhere": true}`)

Session management:
- Refresh tokens are stored as hashed values in `user_sessions` and can be revoked.
- Access tokens include the session id (`sid`) so `logout` can revoke the current session.

### Dev quickstart
- Create tables: `python scripts/dev_init_db.py`
- Run API: `python scripts/dev_run.py`

### Docker (repo root)
- Start dependencies + API: `docker compose up --build`
- Initialize tables (one-time): `docker compose exec api-gateway python scripts/dev_init_db.py`

## Incident Workspace (Module 2)
APIs:
- `POST /api/v1/incidents`
- `GET /api/v1/incidents`
- `GET /api/v1/incidents/{incident_id}`
- `POST /api/v1/incidents/{incident_id}/attachments` (multipart: `kind` + `file`)
- `GET /api/v1/incidents/{incident_id}/timeline`

Attachments:
- `kind=log` triggers auto timeline extraction (cheap regex heuristics; no LLM calls).
- `kind=screenshot` accepts common image types.
- `kind=yaml` accepts yaml/text.

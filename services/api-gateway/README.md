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

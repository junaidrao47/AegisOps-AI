# AegisOps Frontend

Next.js 15 dashboard for the AegisOps API gateway.

## Stack
- Next.js 15 + TypeScript
- TailwindCSS + shadcn/ui-style primitives
- Framer Motion for polish
- Zustand for session state
- React Query for backend caching
- Monaco Editor for logs and analysis input
- Recharts for operational dashboards

## Backend integration
The frontend talks to the API gateway at:
- `http://localhost:8000/api/v1`

Key routes used by the app:
- `GET /health`
- `POST /auth/register`
- `POST /auth/login`
- `POST /auth/refresh`
- `POST /auth/logout`
- `GET /incidents`
- `POST /incidents`
- `GET /orchestrator/health`
- `POST /orchestrator/analyze`
- `POST /logs/detect-source`
- `POST /logs/process-brief`
- `POST /logs/upload`

## Setup
1. Copy `.env.example` to `.env.local`
2. Install dependencies
3. Run `npm run dev`

## Notes
- The app stores JWT tokens in browser storage for local demo use.
- For production, replace local storage with a more secure session strategy.

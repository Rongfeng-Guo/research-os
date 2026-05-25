# Deployment Guide

## Current readiness

This application is ready for server deployment as a small-scale manual workflow service.

Verified locally:

- `cd backend && pytest -q` -> `26 passed`
- `cd frontend && npm run build` -> passes

Supported production use today:

- Single-user or low-concurrency team usage
- Manual source upload and search
- Manual extraction, note generation, suggestion review, snapshot export/import
- In-process automatic refresh for due projects on a single app instance
- In-process automatic digest generation for owners with digest-enabled projects
- Digest delivery status tracking with markdown download preparation and Obsidian-ready markdown export packaging

Not supported for production expectations yet:

- OCR or scanned-PDF parsing beyond section-aware text extraction
- Distributed or multi-instance scheduler coordination
- Real outbound digest delivery such as email, webhook, or direct external vault sync
- High-concurrency multi-tenant workloads

## Required production files

Create these files from the examples:

- `backend/.env.production`
- `frontend/.env.production`

Recommended values:

### `backend/.env.production`

```env
APP_ENV=production
LOG_LEVEL=INFO
LOG_FORMAT=plain
DATABASE_URL=sqlite:///./data/research_os.db
CORS_ALLOW_ORIGINS=https://research.example.com

PAPER_DISCOVERY_PROVIDER=mock
PAPER_DISCOVERY_ALLOW_FALLBACK=true
PAPER_DISCOVERY_TIMEOUT_SECONDS=20
PAPER_SEARCH_LIMIT=8

EXTRACTION_PROVIDER=mock
EXTRACTION_ALLOW_FALLBACK=true

SCHEDULER_ENABLED=true
SCHEDULER_POLL_SECONDS=60
DIGEST_WINDOW_DAYS=7
```

If you want real provider behavior later, add:

```env
OPENAI_API_KEY=...
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini
OPENALEX_EMAIL=ops@example.com
```

### `frontend/.env.production`

```env
NEXT_PUBLIC_API_BASE=https://research.example.com/api
```

## Docker Compose deployment

For a single-domain setup behind Nginx:

```powershell
docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d
```

What this does:

- `frontend` serves the Next.js production app internally on port `3000`
- `backend` serves FastAPI internally on port `8000`
- `nginx` exposes port `80`
- `/` routes to frontend
- `/api/` routes to backend

Production files added for this flow:

- `docker-compose.prod.yml`
- `deploy/nginx.conf`

## Reverse proxy notes

If you already have an external Nginx, Caddy, or Traefik instance:

- point UI traffic to the frontend container
- point `/api/` to the backend container
- keep `NEXT_PUBLIC_API_BASE` aligned with the public API path
- keep backend `CORS_ALLOW_ORIGINS` aligned with the real frontend origin

## Server acceptance checklist

Run this after deployment:

1. Create a real account through `POST /auth/register` or your own bootstrap step.
2. Open `/login` and sign in with that account.
3. Create a new project.
4. Upload a text source.
5. Run extraction and wait for progress to complete.
6. Generate a note.
7. Refresh topic or update suggestion status.
8. Apply one suggestion or a selected section subset.
9. Export a snapshot.
10. Import that snapshot from the project library.

Expected result:

- no 4xx/5xx errors during the main flow
- evidence cards appear
- note renders and updates
- imported snapshot creates a new restored project

## Operational cautions

- Text-based PDF upload is supported, but scanned or image-only PDFs still return a parsing error.
- Automatic refresh and digest generation exist only as a single-process in-app scheduler. If you run multiple backend replicas, disable it or introduce leader/lock coordination first.
- SQLite is fine for a lightweight deployment, but not for larger concurrent traffic.
- The built-in demo account is not created in production mode.

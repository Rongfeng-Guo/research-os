# Research OS

Research OS is a research workspace for collecting papers, extracting evidence, maintaining structured notes, and reviewing updates over time.

It is designed around a simple workflow:

`sources -> evidence cards -> topic note -> review -> version history -> digest`

## Features

- Project and topic management
- Paper search with provider abstraction
- Text, markdown, and PDF source upload
- Structured evidence extraction
- Evidence review, editing, and pinning
- Section-based note generation and editing
- Update suggestions with selective apply
- Note version history and comparison
- Project snapshot export and import
- Project dashboard and weekly digests
- Scheduled refresh and digest preferences

## Stack

- Backend: FastAPI + SQLModel + SQLite
- Frontend: Next.js App Router + React
- Deployment: Docker Compose + Nginx production example

## Local development

### Backend

```powershell
cd backend
python -m pip install --index-url https://pypi.org/simple -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

### Common commands

```powershell
make backend-install
make backend-run
make backend-test
make frontend-install
make frontend-run
make frontend-build
make docker-up
make docker-up-prod
make docker-down
```

## Default URLs

- Frontend: `http://127.0.0.1:3000`
- Backend: `http://127.0.0.1:8000`
- Health: `http://127.0.0.1:8000/health`
- Ready: `http://127.0.0.1:8000/health/ready`

## Environment files

### `backend/.env.example`

```env
APP_ENV=development
LOG_LEVEL=INFO
LOG_FORMAT=plain
DATABASE_URL=sqlite:///./research_os.db
CORS_ALLOW_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

PAPER_DISCOVERY_PROVIDER=mock
PAPER_DISCOVERY_ALLOW_FALLBACK=true
PAPER_DISCOVERY_TIMEOUT_SECONDS=20
PAPER_SEARCH_LIMIT=8

EXTRACTION_PROVIDER=mock
EXTRACTION_ALLOW_FALLBACK=true

# OPENAI_API_KEY=
# OPENAI_BASE_URL=https://api.openai.com/v1
# OPENAI_MODEL=gpt-4o-mini
# OPENALEX_EMAIL=
```

### `backend/.env.production.example`

```env
APP_ENV=production
LOG_LEVEL=INFO
LOG_FORMAT=plain
DATABASE_URL=sqlite:///./data/research_os.db
CORS_ALLOW_ORIGINS=https://your-domain.example
```

### `frontend/.env.local.example`

```env
NEXT_PUBLIC_API_BASE=http://localhost:8000
```

### `frontend/.env.production.example`

```env
NEXT_PUBLIC_API_BASE=https://your-api.example
```

## Notes

- Do not commit local runtime files such as SQLite databases, `.env` files, build output, or local logs.
- Use `backend/.env.example` and `frontend/.env.local.example` as the starting point for local setup.
- The demo account `test@example.com` / `password123` is a development-only convenience and is seeded only when `APP_ENV=development`.
- Production or public deployments should create real accounts through `POST /auth/register` or another explicit bootstrap path.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).

## Weekly dashboard and digest

The homepage dashboard surfaces:

- Recent projects
- Stale projects
- Pending suggestions
- Locked-section attention
- Recent evidence
- Recent note versions
- Recommended next actions

Weekly digests are available through:

- `POST /workspace/digests/generate?days=7`
- `GET /workspace/digests`

Automatic digest generation:

- runs from the same in-process scheduler used for auto refresh
- respects per-project `digest_enabled`
- generates one owner-scoped digest per configured digest window

Digest delivery today:

- `POST /workspace/digests/{id}/deliver`
- supports `download_markdown`
- supports `obsidian_placeholder`
- records delivery status and last delivery timestamp on the digest

Digest summaries include:

- Projects updated
- New papers found and added
- Evidence growth
- Accepted and rejected evidence counts
- Notes updated
- Pending update suggestions
- Locked sections awaiting review
- Recommended next actions

## Refresh preferences

Each project supports:

- `auto_refresh_enabled`
- `refresh_cadence`
- `digest_enabled`
- `last_refreshed_at`
- `next_refresh_due_at`

Supported cadence values:

- `manual_only`
- `daily`
- `weekly`
- `custom`

The product is still manual-first, but a lightweight in-process scheduler can now trigger due refresh jobs for enabled projects.

## Generation modes

Supported note generation modes:

- `accepted_only`
- `all_non_rejected`
- `accepted_plus_pinned_priority`
- `pinned_only`

Recommended defaults:

- High-quality maintenance: `accepted_only`
- Broader exploration: `all_non_rejected`

## Note maintenance

The note workflow supports:

- Section editing
- Section lock and unlock
- Section-level diff review
- Apply one suggestion
- Apply accepted suggestions for one section
- Apply selected accepted suggestions inside one section
- Apply all accepted suggestions
- Version history
- Version comparison

Locked sections are never silently overwritten.

## Export and backup

Project snapshot export:

- `GET /projects/{id}/export`

Project snapshot import:

- `POST /projects/import`
- Project library UI: `Import snapshot`

Export bundle includes:

- Project data
- Source metadata
- Evidence cards
- Topic note
- Update runs
- Suggestions
- Note versions

## Docker

For a more production-like local stack:

```powershell
docker compose up --build
```

The repo includes:

- Backend Dockerfile
- Frontend Dockerfile
- Full-stack `docker-compose.yml`
- Production override `docker-compose.prod.yml`
- Sample reverse proxy config `deploy/nginx.conf`
- Persistent backend volume
- Production-style env wiring

See [DEPLOYMENT.md](DEPLOYMENT.md) for server deployment and acceptance steps.

## Migration strategy

The project currently uses a lightweight migration helper instead of full Alembic.

Principles:

- Non-destructive schema evolution
- Safe default values
- Old data compatibility in serialization
- Automatic backfill where practical

Example compatibility fix already handled:

- `EvidenceCard.extracted_at = NULL` no longer breaks project pages

## Pages

- `/`
- `/digests`
- `/projects`
- `/projects/new`
- `/projects/[id]`
- `/projects/[id]/evidence`
- `/projects/[id]/note`
- `/projects/[id]/history`

## Verification

```powershell
cd backend
pytest -q
```

- `python -m compileall app` passes
- `cd frontend && npm run build` passes
- `cd backend && pytest -q` passes

## Known limitations

- PDF parsing supports text-based PDFs only; scanned or image-only PDFs are not supported yet
- Automatic refresh and digest generation use a single-process in-app scheduler and are not a distributed job system
- Digest delivery supports local markdown export and Obsidian-ready markdown packaging, but not direct email or external sync
- Migration is still a lightweight helper, not Alembic
- OpenAI extraction is still synchronous
- Snapshot import restores into a new project copy and does not merge into an existing project
- SQLite is intended for lightweight deployment, not high-concurrency traffic

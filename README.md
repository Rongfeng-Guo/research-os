# Research OS

Research OS is a structured research workspace for turning a stream of papers into durable project knowledge.

Instead of treating literature review as a single opaque chat interaction, the system keeps each stage explicit and inspectable:

`source acquisition -> evidence extraction -> note synthesis -> review -> version history -> digest delivery`

The result is a workflow that is more auditable than a generic AI notebook and more operational than a folder of ad hoc markdown files.

## Why it exists

Most research tooling breaks down in one of two ways:

- it stores documents, but not reasoning
- it generates summaries, but not a maintainable knowledge base

Research OS is designed to sit between those extremes. It organizes work around projects, preserves source provenance, stores structured evidence, and keeps topic notes under iterative revision rather than one-shot generation.

That makes it suitable for:

- ongoing literature surveillance
- topic mapping and synthesis
- project-centric evidence review
- building notes that can be exported, delivered, and versioned over time

## Product model

At a high level, a project in Research OS moves through five persistent layers:

1. `Sources`
   Papers can be searched, uploaded, linked to projects, and revisited later.
2. `Evidence`
   Structured evidence cards capture claims, methods, datasets, limitations, and open questions.
3. `Notes`
   Section-based project notes are generated and revised with explicit history.
4. `Review`
   Suggestions, locks, manual edits, and evidence pinning keep human control in the loop.
5. `Delivery`
   Workspace digests and note exports move research outputs into downstream systems such as markdown bundles, Obsidian, email, or webhooks.

This architecture is deliberate: notes are not the only artifact. The system preserves the intermediate reasoning surface that produced them.

## Core capabilities

### Source ingestion and project organization

- Create project-scoped research workspaces
- Search for papers through a provider abstraction
- Upload text, markdown, and PDF files
- Maintain a project-level source library
- Export and import project snapshots

### Evidence extraction and review

- Extract structured evidence from source text
- Preserve section-aware source context
- Review, edit, and pin evidence cards
- Track extraction and refresh runs explicitly

### Note generation and revision

- Generate section-based topic notes
- Edit sections manually
- Lock and unlock sections selectively
- Propose targeted update suggestions
- Track version history and compare revisions over time

### Digesting and outbound delivery

- Generate workspace digests
- Download markdown or bundle exports
- Export notes and digests directly into an Obsidian vault
- Deliver digests through email or webhook integrations

## System architecture

The repository is intentionally straightforward:

```text
backend/   FastAPI application, SQLModel models, services, migrations, tests
frontend/  Next.js App Router UI and client workflows
deploy/    Production Nginx example and deployment assets
```

Current stack:

- Backend: FastAPI, SQLModel, Alembic, SQLite
- Frontend: Next.js, React, Tailwind CSS
- Deployment: Docker Compose, Nginx example configuration

The current implementation is optimized for single-user or small-team self-hosted use. It runs end to end locally without requiring external managed infrastructure.

## Request flow and data model

The main runtime path looks like this:

1. Create a project around a topic, lab stream, or literature watchlist.
2. Add sources from uploads or provider-backed search.
3. Extract evidence into structured cards.
4. Review or pin the evidence that should influence the note.
5. Generate or revise the project note.
6. Inspect changes through note history, freshness signals, and workspace digests.
7. Export or deliver outputs to downstream systems.

The core persisted entities are:

- `Project`
- `SourcePaper`
- `ProjectPaper`
- `EvidenceCard`
- `TopicNote`
- `TopicNoteVersion`
- `UpdateRun`
- `WorkspaceDigest`

This separation is one of the project's main strengths. It keeps provenance, generation state, and exported outputs distinct instead of collapsing them into a single mutable summary.

## Current operating model

Research OS already supports a practical end-to-end workflow for local deployment:

- backend API
- frontend application
- SQLite persistence
- in-process refresh and digest scheduling
- note and digest export flows
- Alembic-managed schema evolution

Operationally, the project should currently be understood as:

- production-minded in structure
- self-hostable today
- still maturing in orchestration, OCR, and multi-user depth

## Quick start

### Backend

```powershell
cd backend
python -m pip install --index-url https://pypi.org/simple -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload
```

### Frontend

```powershell
cd frontend
npm install
Copy-Item .env.local.example .env.local
npm run dev
```

### Default local endpoints

- Frontend: `http://127.0.0.1:3000`
- Backend: `http://127.0.0.1:8000`
- Health: `http://127.0.0.1:8000/health`
- Ready: `http://127.0.0.1:8000/health/ready`

## Common commands

```powershell
make backend-install
make backend-run
make backend-test
make backend-migrate
make backend-migration-create
make frontend-install
make frontend-run
make frontend-build
make docker-up
make docker-up-prod
make docker-down
```

## Configuration surface

Start from the shipped environment templates:

- `backend/.env.example`
- `backend/.env.production.example`
- `frontend/.env.local.example`
- `frontend/.env.production.example`

In development, a seeded demo account is available only when `APP_ENV=development`:

- `test@example.com`
- `password123`

For public or production deployments, provision real accounts through `POST /auth/register` or your own bootstrap flow.

## Delivery and export model

Research OS treats delivery as a first-class concern rather than an afterthought.

### Digest delivery targets

- markdown download
- bundle download
- direct Obsidian vault export
- server-side email delivery
- server-side webhook delivery

### Note delivery targets

- markdown download
- bundle download
- direct Obsidian vault export

### Relevant endpoints

- `POST /workspace/digests/generate`
- `POST /workspace/digests/{id}/deliver`
- `GET /workspace/digests/{id}/download?format=markdown`
- `GET /workspace/digests/{id}/download?format=bundle`
- `POST /notes/projects/{id}/export`
- `GET /notes/projects/{id}/download?format=markdown`
- `GET /notes/projects/{id}/download?format=bundle`

To enable direct Obsidian export on the backend host:

```powershell
OBSIDIAN_EXPORT_ROOT=C:\path\to\your\vault
OBSIDIAN_EXPORT_DIR=Research OS
```

Typical outbound delivery configuration:

```powershell
DATABASE_MIGRATION_MODE=hybrid
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_FROM_EMAIL=ops@example.com
SMTP_TO_EMAILS=team@example.com
SMTP_USE_TLS=true
DIGEST_WEBHOOK_URL=https://example.com/hooks/research-os
```

## Database and migrations

The repository has moved to an Alembic-centered migration model.

Supported runtime modes:

- `hybrid`
  Default mode. It bootstraps pre-Alembic legacy databases by stamping the initial baseline and then upgrading through the current Alembic revision chain.
- `alembic`
  Pure Alembic mode for already managed databases.

Health endpoints expose both `database_migration_mode` and `alembic_revision`, which makes migration state visible to operators without shell access.

Standard workflow:

```powershell
cd backend
alembic upgrade head
alembic revision --autogenerate -m "describe change"
```

Further documentation:

- [MIGRATIONS.md](MIGRATIONS.md) for the active migration model
- [LEGACY_MIGRATION.md](LEGACY_MIGRATION.md) for the standalone rescue path used only for very old databases

## Interface and API surface

Primary UI routes:

- `/`
- `/digests`
- `/projects`
- `/projects/new`
- `/projects/[id]`
- `/projects/[id]/evidence`
- `/projects/[id]/note`
- `/projects/[id]/history`

Representative backend endpoints:

- `POST /papers/search`
- `POST /papers/projects/{id}/upload-text`
- `POST /papers/projects/{id}/upload-file`
- `POST /papers/projects/{id}/extract`
- `POST /notes/projects/{id}/generate`
- `POST /projects/{id}/refresh`
- `GET /projects/{id}/export`
- `POST /projects/import`

## Deployment

For a production-like local stack:

```powershell
docker compose up --build
```

Repository assets include:

- `backend/Dockerfile`
- `frontend/Dockerfile`
- `docker-compose.yml`
- `docker-compose.prod.yml`
- `deploy/nginx.conf`

Deployment details live in [DEPLOYMENT.md](DEPLOYMENT.md).

## Verification

The repository is regularly validated with:

- `cd backend && pytest -q`
- `cd backend && python -m compileall app scripts`
- `cd frontend && npm run build`

## Known limitations

- PDF parsing currently assumes text-based PDFs; OCR for scanned PDFs is not implemented yet
- Refresh, extraction, and digest scheduling still run in-process rather than through a dedicated job queue
- SQLite is appropriate for lightweight deployments, not high-concurrency multi-tenant traffic
- Direct Obsidian export writes to the backend host filesystem and assumes a trusted self-hosted environment
- Email and webhook delivery currently rely on trusted server-side credentials and endpoints

## Roadmap direction

The most natural next-stage evolution is:

- OCR support for scanned PDFs
- background job infrastructure for refresh and extraction workloads
- stronger multi-user and multi-instance deployment support
- more durable external sync and delivery integrations

## Additional documentation

- [CONTRIBUTING.md](CONTRIBUTING.md)
- [SECURITY.md](SECURITY.md)
- [DEPLOYMENT.md](DEPLOYMENT.md)
- [MIGRATIONS.md](MIGRATIONS.md)
- [LEGACY_MIGRATION.md](LEGACY_MIGRATION.md)

## License

This project is released under the MIT License. See [LICENSE](LICENSE).

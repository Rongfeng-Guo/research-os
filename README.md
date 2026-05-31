# Research OS

Research OS is a workspace for collecting papers, extracting evidence, maintaining topic notes, and reviewing how a research project changes over time.

It is built for a practical workflow:

`sources -> evidence cards -> topic note -> review -> version history -> digest`

## What it does

- Organizes work by project and topic
- Adds sources from search results or direct uploads
- Extracts structured evidence cards from source text
- Builds and maintains section-based notes
- Tracks note revisions and update suggestions
- Summarizes recent activity in a dashboard and digest view

## Core capabilities

### Source management

- Paper search with provider abstraction
- Text, markdown, and PDF uploads
- Project-level source library
- Snapshot export and import

### Evidence workflow

- Structured evidence extraction
- Review states for evidence cards
- Manual editing and pinning
- Section-aware source context for extracted evidence

### Note workflow

- Section-based note generation
- Manual section editing
- Section lock and unlock controls
- Update suggestions with selective apply
- Version history and comparison

### Project review

- Workspace dashboard
- Project health and freshness signals
- Manual and scheduled refresh preferences
- Period digests with markdown export

## Current status

This repository already runs end to end for local use:

- backend API
- frontend application
- SQLite persistence
- local scheduler for refresh and digest generation
- markdown export flows for snapshots and digests

The current implementation is best suited to single-user or small-scale deployments.

## How it works

At a high level, the application follows this flow:

1. Create a project around a topic or ongoing literature stream.
2. Add sources from search results or direct uploads.
3. Run extraction to turn source text into structured evidence cards.
4. Review and pin evidence that should shape the note.
5. Generate or update a section-based topic note.
6. Inspect changes through note versions, suggestions, dashboard signals, and digests.

The backend keeps the workflow explicit instead of hiding it behind one opaque generation step. Sources, evidence, notes, update runs, and digests all remain visible as separate artifacts.

## Stack

- Backend: FastAPI, SQLModel, SQLite
- Frontend: Next.js App Router, React, Tailwind CSS
- Deployment: Docker Compose, Nginx example configuration

## Project structure

```text
backend/   FastAPI app, models, services, tests
frontend/  Next.js app, components, client-side flows
deploy/    Production Nginx example
```

## Quick start

### 1. Backend

```powershell
cd backend
python -m pip install --index-url https://pypi.org/simple -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload
```

### 2. Frontend

```powershell
cd frontend
npm install
Copy-Item .env.local.example .env.local
npm run dev
```

### 3. Open the app

- Frontend: `http://127.0.0.1:3000`
- Backend: `http://127.0.0.1:8000`
- Health: `http://127.0.0.1:8000/health`
- Ready: `http://127.0.0.1:8000/health/ready`

## Common commands

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

## Environment files

Use the example files as the starting point for local or production setup:

- `backend/.env.example`
- `backend/.env.production.example`
- `frontend/.env.local.example`
- `frontend/.env.production.example`

Local development uses a seeded demo account only when `APP_ENV=development`:

- `test@example.com`
- `password123`

For public or production deployment, create real accounts through `POST /auth/register` or your own bootstrap flow.

## Key routes

### UI pages

- `/`
- `/digests`
- `/projects`
- `/projects/new`
- `/projects/[id]`
- `/projects/[id]/evidence`
- `/projects/[id]/note`
- `/projects/[id]/history`

### Backend endpoints

- `POST /papers/search`
- `POST /papers/projects/{id}/upload-text`
- `POST /papers/projects/{id}/upload-file`
- `POST /papers/projects/{id}/extract`
- `POST /notes/projects/{id}/generate`
- `POST /projects/{id}/refresh`
- `GET /projects/{id}/export`
- `POST /projects/import`
- `POST /workspace/digests/generate`
- `POST /workspace/digests/{id}/deliver`

## Digest and export support

Digests support:

- project activity summary
- pending review tracking
- markdown download export
- Obsidian-ready markdown packaging with frontmatter
- optional direct Obsidian file export when `OBSIDIAN_EXPORT_ROOT` is configured

To enable direct vault export on the backend host:

```powershell
OBSIDIAN_EXPORT_ROOT=C:\path\to\your\vault
OBSIDIAN_EXPORT_DIR=Research OS
```

Then use `POST /workspace/digests/{id}/deliver` with `{"target":"obsidian_file"}` to write the digest into that vault-relative folder.

Project backup support includes:

- full project snapshot export
- snapshot import into a new project copy

## Data model

The main objects in the system are:

- `Project` for the research topic and refresh preferences
- `SourcePaper` for uploaded or discovered source material
- `ProjectPaper` for the link between projects and sources
- `EvidenceCard` for extracted claims, methods, datasets, limitations, and open questions
- `TopicNote` for the current working note
- `TopicNoteVersion` for note history
- `UpdateRun` for extraction and refresh progress
- `WorkspaceDigest` for period summaries

## Docker

For a production-like local stack:

```powershell
docker compose up --build
```

The repository includes:

- `backend/Dockerfile`
- `frontend/Dockerfile`
- `docker-compose.yml`
- `docker-compose.prod.yml`
- `deploy/nginx.conf`

For deployment details, see [DEPLOYMENT.md](DEPLOYMENT.md).

## Verification

Verified locally:

- `cd backend && pytest -q`
- `cd frontend && npm run build`
- `cd backend && python -m compileall app`

## Known limitations

- PDF parsing currently supports text-based PDFs only
- OCR for scanned PDFs is not implemented yet
- Refresh and digest scheduling run in-process on a single backend instance
- Digest delivery does not yet include direct email, webhook, or external vault sync
- Direct Obsidian export writes to the backend host filesystem and is intended for trusted single-user or self-hosted setups
- The schema migration approach is lightweight and does not use Alembic
- SQLite is intended for lightweight deployment, not high-concurrency traffic

## Roadmap

Planned next steps:

- OCR support for scanned PDFs
- Stronger outbound digest delivery such as email or webhook targets
- Better multi-user and multi-instance deployment support
- More robust database migration tooling

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for setup, validation, and pull request expectations.

## Security

See [SECURITY.md](SECURITY.md) for vulnerability reporting guidance.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).

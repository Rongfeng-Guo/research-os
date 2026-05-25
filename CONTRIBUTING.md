# Contributing

Thanks for contributing to Research OS MVP.

## Development setup

Backend:

```powershell
cd backend
python -m pip install --index-url https://pypi.org/simple -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload
```

Frontend:

```powershell
cd frontend
npm install
Copy-Item .env.local.example .env.local
npm run dev
```

Default local URLs:

- Frontend: `http://127.0.0.1:3000`
- Backend: `http://127.0.0.1:8000`

## Development notes

- Keep local environment files out of commits. Use the example env files as the source of truth.
- The default demo account is created only when `APP_ENV=development`.
- Production deployments should create real user accounts through the registration flow or an explicit bootstrap path.

## Validation

Backend tests:

```powershell
cd backend
python -m pytest -q
```

Frontend production build:

```powershell
cd frontend
npm run build
```

Useful root-level shortcuts:

```powershell
make backend-test
make frontend-build
make docker-up
```

## Pull requests

- Keep changes scoped and explain the user-visible impact.
- Update docs when behavior or setup changes.
- Include verification details for tests, build output, or manual checks.

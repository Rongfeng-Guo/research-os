PYTHON_INDEX_URL ?= https://pypi.org/simple

.PHONY: backend-install backend-run backend-test backend-migrate backend-migration-create frontend-install frontend-run frontend-build docker-up docker-up-prod docker-down

backend-install:
	cd backend && python -m pip install --index-url $(PYTHON_INDEX_URL) -r requirements.txt

backend-run:
	cd backend && uvicorn app.main:app --reload

backend-test:
	cd backend && pytest -q

backend-migrate:
	cd backend && alembic upgrade head

backend-migration-create:
	cd backend && alembic revision --autogenerate -m "$(MESSAGE)"

frontend-install:
	cd frontend && npm install

frontend-run:
	cd frontend && npm run dev

frontend-build:
	cd frontend && npm run build

docker-up:
	docker compose up --build

docker-up-prod:
	docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d

docker-down:
	docker compose down

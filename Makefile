# One command to run everything:   make dev
#   → env files → deps → Postgres (docker) → migrations → backend :8000 + UI :3000   (Ctrl+C stops both)

.PHONY: dev env install docker-up docker-down migrate backend frontend

dev: env install docker-up migrate
	@echo ""
	@echo "  UI   → http://localhost:3000"
	@echo "  API  → http://localhost:8000/docs"
	@echo "  Ctrl+C stops both  ·  'make docker-down' stops the database"
	@echo ""
	@$(MAKE) -j2 backend frontend

# Create env files from the examples on first run (never overwrites existing ones)
env:
	@[ -f .env.local ] || { cp .env.example .env.local && echo "  created .env.local"; }
	@[ -f backend/.env ] || { cp backend/.env.example backend/.env && echo "  created backend/.env  → set your LLM / embedding settings"; }

# Install dependencies only when missing / out of date (fast no-op otherwise)
install:
	@[ -d node_modules ] || npm install
	@cd backend && uv sync --frozen --quiet

# --wait blocks until the healthcheck passes, so migrations never race the DB
docker-up:
	docker compose -f backend/docker-compose.yml up -d --wait

docker-down:
	docker compose -f backend/docker-compose.yml down

migrate:
	cd backend && uv run --frozen python -m alembic upgrade head

backend:
	cd backend && $(MAKE) dev

frontend:
	npm run dev

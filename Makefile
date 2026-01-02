.PHONY: help install install-frontend backend frontend redis redis-stop migrate \
	build-api build-frontend build-images dev compose-up compose-down \
	compose-logs compose-migrate

PYTHON ?= python3
PIP := $(PYTHON) -m pip
DOCKER ?= docker
COMPOSE ?= docker compose
REDIS_IMAGE ?= redis:7.2.4-alpine

API_HOST ?= 0.0.0.0
API_PORT ?= 8000
FRONTEND_API_URL ?= /api/v1
FRONTEND_VERSION ?= dev

help:
	@printf "%s\n" \
		"Targets:" \
		"  install          Install backend deps (editable)" \
		"  install-frontend Install frontend deps" \
		"  migrate          Run Alembic migrations" \
		"  redis            Start Redis in Docker (named splatvote-redis)" \
		"  redis-stop       Stop Redis container" \
		"  backend          Run FastAPI dev server" \
		"  frontend         Run React dev server" \
		"  dev              Run backend + frontend (assumes Redis already up)" \
		"  compose-up       Start local stack with docker compose" \
		"  compose-down     Stop local stack and remove containers" \
		"  compose-logs     Tail docker compose logs" \
		"  compose-migrate  Run Alembic migrations in docker compose" \
		"  build-api        Build vote-api image (local tag)" \
		"  build-frontend   Build vote-frontend image (local tag)" \
		"  build-images     Build both images"

install:
	$(PIP) install -e .

install-frontend:
	cd src/vote_frontend && npm install

migrate:
	$(PYTHON) -m alembic upgrade head

redis:
	$(DOCKER) run --rm -d --name splatvote-redis -p 6379:6379 $(REDIS_IMAGE)

redis-stop:
	-$(DOCKER) stop splatvote-redis

backend:
	$(PYTHON) -m uvicorn vote_api.app:app --reload --app-dir src --host $(API_HOST) --port $(API_PORT)

frontend:
	cd src/vote_frontend && npm start

dev:
	@printf "%s\n" "Starting backend + frontend. Run 'make redis' in another terminal if needed."
	$(MAKE) -j2 backend frontend

compose-up:
	$(COMPOSE) up --build

compose-down:
	$(COMPOSE) down

compose-logs:
	$(COMPOSE) logs -f

compose-migrate:
	$(COMPOSE) run --rm migrate

build-api:
	$(DOCKER) build -f dockerfiles/dockerfile.vote-api -t vote-api:local .

build-frontend:
	$(DOCKER) build -f dockerfiles/dockerfile.vote-frontend \
		--build-arg REACT_APP_VERSION=$(FRONTEND_VERSION) \
		--build-arg REACT_APP_API_URL=$(FRONTEND_API_URL) \
		-t vote-frontend:local .

build-images: build-api build-frontend

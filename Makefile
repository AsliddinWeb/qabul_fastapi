SHELL := /bin/bash

COMPOSE      := docker compose
COMPOSE_DEV  := docker compose -f docker-compose.yml -f docker-compose.dev.yml

.PHONY: help init up down restart logs ps build rebuild \
        migrate makemigration seed superadmin \
        backend-shell db-shell redis-shell \
        dev dev-down test lint format clean

help:
	@echo ""
	@echo "  XIU Admission System — Make targets"
	@echo "  ----------------------------------"
	@echo "  make init          - copy .env.example -> .env (first time only)"
	@echo "  make up            - start production stack"
	@echo "  make down          - stop stack"
	@echo "  make restart       - restart all services"
	@echo "  make logs          - tail logs (all services)"
	@echo "  make ps            - show running services"
	@echo "  make build         - build images"
	@echo "  make rebuild       - rebuild images (no cache)"
	@echo ""
	@echo "  make dev           - start dev stack (hot reload)"
	@echo "  make dev-down      - stop dev stack"
	@echo ""
	@echo "  make migrate                - alembic upgrade head"
	@echo "  make makemigration m=\"msg\"  - alembic revision --autogenerate"
	@echo "  make seed                   - seed dictionaries"
	@echo "  make superadmin             - create initial superadmin"
	@echo ""
	@echo "  make backend-shell - bash into backend container"
	@echo "  make db-shell      - psql into postgres"
	@echo "  make redis-shell   - redis-cli"
	@echo ""

init:
	@if [ ! -f .env ]; then cp .env.example .env && echo ".env created — edit secrets before running."; else echo ".env already exists"; fi

up:
	$(COMPOSE) up -d

down:
	$(COMPOSE) down

restart:
	$(COMPOSE) restart

logs:
	$(COMPOSE) logs -f --tail=200

ps:
	$(COMPOSE) ps

build:
	$(COMPOSE) build

rebuild:
	$(COMPOSE) build --no-cache

dev:
	$(COMPOSE_DEV) up -d

dev-down:
	$(COMPOSE_DEV) down

migrate:
	$(COMPOSE) exec backend alembic upgrade head

makemigration:
	$(COMPOSE) exec backend alembic revision --autogenerate -m "$(m)"

seed:
	$(COMPOSE) exec backend python -m scripts.seed_dictionaries

seed-templates:
	$(COMPOSE) exec backend python -m scripts.seed_templates

superadmin:
	$(COMPOSE) exec \
		-e SUPERADMIN_PHONE="$(SUPERADMIN_PHONE)" \
		-e SUPERADMIN_PASSWORD="$(SUPERADMIN_PASSWORD)" \
		-e SUPERADMIN_NAME="$(SUPERADMIN_NAME)" \
		backend python -m scripts.create_superadmin

backend-shell:
	$(COMPOSE) exec backend bash

frontend-shell:
	$(COMPOSE) exec frontend sh

landing-shell:
	$(COMPOSE) exec landing sh

db-shell:
	$(COMPOSE) exec postgres psql -U $${POSTGRES_USER:-admission} -d $${POSTGRES_DB:-admission}

redis-shell:
	$(COMPOSE) exec redis redis-cli

test:
	$(COMPOSE) exec backend pytest -v

lint:
	$(COMPOSE) exec backend ruff check app tests

format:
	$(COMPOSE) exec backend ruff format app tests

clean:
	$(COMPOSE) down -v

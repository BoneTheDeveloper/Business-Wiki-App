# =============================================
# Business Wiki App - Development Commands
# =============================================
# IMPORTANT: All commands must be run inside WSL (Ubuntu)
#   Open WSL terminal, then: cd /mnt/d/Project/Bussiness_Wiki_App
# Usage: make <target>

SHELL := /bin/bash

# Fail early if not running in WSL/Linux
ifneq ($(shell uname -s 2>/dev/null),Linux)
$(error ERROR: This Makefile requires WSL/Linux. Run from WSL: wsl -d Ubuntu)
endif

DC           := docker compose -f docker/docker-compose.yml
BACKEND_DIR  := backend
FRONTEND_DIR := frontend
CHAINLIT_DIR := chainlit

.PHONY: help install install-backend install-frontend install-chainlit \
        supabase supabase-stop \
        dev-infra dev-backend dev-frontend dev-chainlit \
        playground playground-stop playground-logs playground-build \
        up down logs build clean test

# --- Default ---
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}'

# --- Dependencies ---
install: install-backend install-frontend install-chainlit ## Install all deps

install-backend: ## Sync backend Python deps
	cd $(BACKEND_DIR) && uv sync

install-frontend: ## Install frontend Node deps
	cd $(FRONTEND_DIR) && pnpm install

install-chainlit: ## Sync chainlit Python deps
	cd $(CHAINLIT_DIR) && uv sync

# --- Local Supabase ---
supabase: ## Start local Supabase
	supabase start

supabase-stop: ## Stop local Supabase
	supabase stop

# --- Local Dev (no Docker) ---
dev-infra: ## Start Redis + MinIO only (Docker)
	$(DC) up -d redis minio

dev-backend: ## Run backend (port 8000)
	cd $(BACKEND_DIR) && PLAYGROUND_ENABLED=true uv run uvicorn app.main:app --reload --port 8000

dev-frontend: ## Run frontend (port 5173)
	cd $(FRONTEND_DIR) && pnpm run dev

dev-chainlit: ## Run chainlit (port 8001)
	cd $(CHAINLIT_DIR) && uv run chainlit run app.py --headless --port 8001

# --- Docker Playground (containerized) ---
playground: ## Start playground (Redis + MinIO + backend + chainlit in Docker)
	@echo "==> Starting playground..."
	@PLAYGROUND_ENABLED=true $(DC) up -d redis minio backend chainlit
	@echo "==> Playground running!"
	@echo "    backend:  http://localhost:8000"
	@echo "    chainlit: http://localhost:8001"
	@echo "    stop:     make playground-stop"
	@echo "    logs:     make playground-logs"

playground-stop: ## Stop playground containers
	@$(DC) down
	@echo "==> Playground stopped."

playground-logs: ## Tail playground logs
	$(DC) logs -f backend chainlit

playground-build: ## Rebuild playground images
	$(DC) build backend chainlit

# --- Docker Compose (all services) ---
up: ## Start core services via Docker
	$(DC) up -d

down: ## Stop and remove containers
	$(DC) down

logs: ## Tail docker compose logs
	$(DC) logs -f

build: ## Build (or rebuild) docker images
	$(DC) build

clean: ## Remove containers and volumes
	$(DC) down -v

# --- Testing ---
test: ## Run backend tests
	cd $(BACKEND_DIR) && uv run pytest

SHELL := /bin/bash

.PHONY: help up down build ps logs topic-create produce bronze

help:
	@echo "Infrastructure:"
	@echo "  make up               - start core (API + Postgres + OpenSearch)"
	@echo "  make up-airflow       - start core + Airflow stack"
	@echo "  make up-rag           - start core + Ollama + Gradio UI"
	@echo "  make up-dashboards    - start core + OpenSearch Dashboards"
	@echo "  make down             - stop stack"
	@echo "  make build            - rebuild images"
	@echo "  make ps               - show containers"
	@echo "  make logs             - tail logs"
	@echo "  make down             - stop stack"
	@echo "  make build            - rebuild images"
	@echo "  make ps               - show containers"
	@echo "  make logs             - tail logs"
	@echo ""
	@echo "Testing:"
	@echo "  make test             - run all tests (unit + api + integration)"
	@echo "  make test-unit        - run unit tests"
	@echo "  make test-api         - run api tests"
	@echo "  make test-integration - run integration tests"
	@echo "  make test-smoke       - run smoke tests (requires external services)"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint             - run ruff linter"
	@echo "  make format           - format code with ruff"
	@echo "  make format-check     - check code formatting"
	@echo "  make typecheck        - run type checker"
	@echo "  make pre-commit-install - install pre-commit hooks"
	@echo "  make pre-commit-run   - run pre-commit on all files"
	@echo ""

up:
	docker compose up -d --build

up-airflow:
	docker compose --profile airflow up -d --build

up-rag:
	docker compose --profile rag up -d

up-dashboards:
	docker compose --profile dashboards up -d

down:
	docker compose down -v

build:
	docker compose build --no-cache

ps:
	docker compose ps

logs:
	docker compose logs -f --tail=200

test:
	docker compose exec api pytest tests/unit tests/api tests/integration -v

test-unit:
	docker compose exec api pytest tests/unit -v

test-api:
	docker compose exec api pytest tests/api -v

test-integration:
	docker compose exec api pytest tests/integration -v

test-smoke:
	docker compose exec api pytest tests/smoke -v

lint:
	uv run ruff check .

format:
	uv run ruff format .

format-check:
	uv run ruff format --check .

typecheck:
	uv run mypy src

pre-commit-install:
	uv run pre-commit install

pre-commit-run:
	uv run pre-commit run --all-files

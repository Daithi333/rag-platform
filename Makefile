SHELL := /bin/bash

.PHONY: help up down build ps logs topic-create produce bronze

help:
	@echo "Infrastructure:"
	@echo "  make up               - start stack"
	@echo "  make up-dashboards    - start stack with OpenSearch Dashboards"
	@echo "  make down             - stop stack"
	@echo "  make build            - rebuild images"
	@echo "  make ps               - show containers"
	@echo "  make logs             - tail logs"
	@echo ""
	@echo "Testing:"
	@echo "  make test             - run all tests"
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

up-dashboards:
	docker compose --profile dashboards up -d --build

down:
	docker compose down -v

build:
	docker compose build --no-cache

ps:
	docker compose ps

logs:
	docker compose logs -f --tail=200

test:
	docker compose exec api pytest -v

test-unit:
	docker compose exec api pytest tests/unit -v

test-api:
	docker compose exec api pytest tests/api -v

test-integration:
	docker compose exec api pytest tests/integration -v

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

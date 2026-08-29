# Scaffolded by agent-builder. PKG = agent_pkg (renamed by skills/1-scaffold).
PKG := agent_pkg
.DEFAULT_GOAL := help

.PHONY: help setup lint test test-unit test-regression test-integration \
        eval obs-up obs-down functions-index smoke

help: ## List targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  %-20s %s\n", $$1, $$2}'

setup: ## Install deps (uv) and pre-commit hook
	uv sync --extra dev --extra dashboard --extra evals
	@cp -n .git/hooks/pre-commit .git/hooks/pre-commit.bak 2>/dev/null || true
	@printf '#!/bin/sh\nmake lint test-unit || exit 1\n' > .git/hooks/pre-commit
	@chmod +x .git/hooks/pre-commit

lint: ## Ruff (incl. mandatory docstrings) + mypy
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy

test: test-unit test-regression test-integration ## All deterministic suites (no tokens)

test-unit: ## Pure-function unit tests
	uv run pytest tests/unit --cov

test-regression: ## Golden-file transform tests
	uv run pytest tests/regression

test-integration: ## Deterministic wiring vs real data-store containers (no model calls)
	uv run pytest tests/integration -m integration

functions-index: ## Regenerate FUNCTIONS.md from src/ docstrings
	uv run python tools/functions_index.py --write
	@git diff --exit-code FUNCTIONS.md >/dev/null || (echo "FUNCTIONS.md updated — review & commit"; true)

eval: ## Run the eval suite (local Ollama judge by default)
	uv run python -m evals.run_evals

obs-up: ## Start observability stack (docker compose)
	docker compose --profile observability up -d

obs-down: ## Stop observability stack
	docker compose --profile observability down

smoke: ## Emit a fake traced agent run to verify observability
	uv run python -m $(PKG).observability.smoke

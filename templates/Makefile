# Scaffolded by agent-builder. PKG = agent_pkg (renamed by skills/1-scaffold).
PKG := agent_pkg
.DEFAULT_GOAL := help

.PHONY: help setup lint test test-unit test-regression test-integration \
        eval obs-up obs-down functions-index smoke context-budget context-rotate \
        arch-snapshot arch-snapshot-commit arch-history route \
        integrations integrations-enable adversarial adversarial-fast

help: ## List targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  %-20s %s\n", $$1, $$2}'

setup: ## Install deps (uv) and pre-commit hook
	uv sync --extra dev --extra dashboard --extra evals
	@cp -n .git/hooks/pre-commit .git/hooks/pre-commit.bak 2>/dev/null || true
	@printf '#!/bin/sh\nmake lint test-unit || exit 1\n' > .git/hooks/pre-commit
	@chmod +x .git/hooks/pre-commit

lint: ## Ruff (incl. mandatory docstrings) + mypy + context budgets
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy
	uv run python tools/context_budget.py --check

test: test-unit test-regression test-integration ## All deterministic suites (no tokens)

test-unit: ## Pure-function unit tests
	uv run pytest tests/unit --cov

test-regression: ## Golden-file transform tests
	uv run pytest tests/regression

test-integration: ## Deterministic wiring vs real data-store containers (no model calls)
	uv run pytest tests/integration -m integration

context-budget: ## Check agent context files are within their line budgets
	uv run python tools/context_budget.py --check

context-rotate: ## Archive overflow CHANGELOG/TODO entries into docs/archive/
	uv run python tools/context_budget.py --rotate

arch-snapshot: ## Verify ARCHITECTURE.md is committed before you rewrite it
	uv run python tools/arch_snapshot.py --check

arch-snapshot-commit: ## Commit pending ARCHITECTURE.md changes (never pushes)
	uv run python tools/arch_snapshot.py --commit

arch-history: ## List past versions of ARCHITECTURE.md
	uv run python tools/arch_snapshot.py --history

integrations: ## What optional MCPs/skills are available, and what would they unlock?
	@uv run python tools/check_integrations.py

integrations-enable: ## Add one catalogued MCP server:  make integrations-enable NAME=context7
	@uv run python tools/check_integrations.py --enable "$(NAME)"

route: ## Which model tier should a task use?  make route T="find the parser"
	@uv run python tools/route_task.py "$(T)"

functions-index: ## Regenerate FUNCTIONS.md from src/ docstrings
	uv run python tools/functions_index.py --write
	@git diff --exit-code FUNCTIONS.md >/dev/null || (echo "FUNCTIONS.md updated — review & commit"; true)

eval: ## Run the eval suite (local Ollama judge by default)
	uv run python -m evals.run_evals

adversarial: ## Full red-team suite — any breach fails the build
	uv run python -m evals.run_evals --only adversarial

adversarial-fast: ## High-signal adversarial subset (for pre-commit / PR)
	uv run python -m evals.run_evals --only adversarial --fast

obs-up: ## Start observability stack (docker compose)
	docker compose --profile observability up -d

obs-down: ## Stop observability stack
	docker compose --profile observability down

smoke: ## Emit a fake traced agent run to verify observability
	uv run python -m $(PKG).observability.smoke

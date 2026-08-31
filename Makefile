.PHONY: help dev dev-tabs test lint clean

# Default target when running just 'make'
.DEFAULT_GOAL := help

help: ## Show available Makefile commands
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

dev: ## Launch full dev environment using tmuxp
	tmuxp load .

dev-tabs: ## Launch dev environment using native terminal tabs
	./start-dev.sh

test: ## Run pytest test suite
	uv run pytest -v

lint: ## Run code checks and formatters
	uv run ruff check .
	uv run ruff format --check .

clean: ## Stop podman containers and clean up temp files
	podman compose down
	find . -type d -name "__pycache__" -exec rm -rf {} +
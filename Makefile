.PHONY: help install install-dev test lint format type-check clean run-example

help: ## Show this help message
	@echo "DFS Fantasy - Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install production dependencies
	uv sync

install-dev: ## Install development dependencies
	uv sync --extra dev

test: ## Run tests
	uv run pytest

test-cov: ## Run tests with coverage
	uv run pytest --cov=src --cov-report=html

lint: ## Run linting
	uv run flake8 src/ examples/

format: ## Format code with black
	uv run black src/ examples/

format-check: ## Check if code is formatted correctly
	uv run black --check src/ examples/

type-check: ## Run type checking with mypy
	uv run mypy src/

check-all: format-check lint type-check ## Run all code quality checks

clean: ## Clean up generated files
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

run-example: ## Run the example data collection script
	uv run python examples/collect_data.py

run-dff-example: ## Run the Daily Fantasy Fuel example script
	uv run python examples/process_dff_csv.py

run-yahoo-example: ## Run the Yahoo DFS contest scraping example script
	uv run python examples/scrape_yahoo_contests.py

run-player-matching: ## Run player matching example
	uv run python examples/player_matching_example.py

dev-setup: ## Set up development environment
	./scripts/dev-setup.sh

pre-commit: ## Install pre-commit hooks
	uv run pre-commit install

pre-commit-run: ## Run pre-commit on all files
	uv run pre-commit run --all-files

venv: ## Activate virtual environment
	@echo "To activate the virtual environment, run:"
	@echo "source .venv/bin/activate"
	@echo ""
	@echo "Or use uv run to run commands in the virtual environment:"
	@echo "uv run python script.py" 
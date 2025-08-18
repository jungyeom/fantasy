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

run-lineup-optimizer: ## Run Yahoo DFS lineup optimizer
	uv run python examples/run_lineup_optimizer.py

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

create-dummy-projections: ## Create dummy projections CSV file
	uv run python examples/create_dummy_projections.py 

run-pipeline: ## Run complete DFS pipeline (data collection + lineup optimization)
	uv run python examples/run_pipeline.py

run-pipeline-low-fee: ## Run DFS pipeline with entry fees ≤$0.5
	uv run python -c "import asyncio, sys; sys.path.insert(0, 'src'); from data_collection import DFSPipeline, SportType; pipeline = DFSPipeline(); asyncio.run(pipeline.run_pipeline(SportType.NFL, max_entry_fee=0.5))"

test-slate-types: ## Test slate types and budget handling for single vs multi game contests
	uv run python -c "import asyncio, sys; sys.path.insert(0, 'src'); from data_collection import YahooDFSCollector, SportType; collector = YahooDFSCollector(); asyncio.run(collector.collect_contests(SportType.NFL, multi_entry_only=False))"

test-single-vs-multi-optimizer: ## Test lineup optimizer with single game vs multi game contests
	uv run python -c "import sys; sys.path.insert(0, 'src'); from data_collection.lineup_optimizer import optimize_lineups; from pathlib import Path; yahoo_csv = Path('examples/yahoo_players.csv'); multi_info = {'contest_id': 'test', 'contest_name': 'Multi Game', 'entry_fee': 1.0, 'slate_type': 'MULTI_GAME', 'salary_cap': 200}; single_info = {'contest_id': 'test', 'contest_name': 'Single Game', 'entry_fee': 0.25, 'slate_type': 'SINGLE_GAME', 'salary_cap': 135}; print('Testing Multi Game...'); multi = optimize_lineups(str(yahoo_csv), multi_info, 1); print('Testing Single Game...'); single = optimize_lineups(str(yahoo_csv), single_info, 1); print(f'Multi: ${multi[0][\"total_salary\"]:,}, Single: ${single[0][\"total_salary\"]:,}')" 
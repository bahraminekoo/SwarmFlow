.PHONY: install dev test lint format run dashboard clean

install:
	pip install -e .

dev:
	pip install -e ".[dev]"

test:
	pytest -v --tb=short

test-cov:
	pytest -v --cov=swarmflow --cov-report=term-missing

lint:
	ruff check src/ tests/
	mypy src/

format:
	ruff format src/ tests/
	ruff check --fix src/ tests/

run:
	swarmflow launch hedge-fund --goal "Analyze AAPL, MSFT, NVDA for Q2 2026"

dashboard:
	swarmflow dashboard --port 8080

clean:
	rm -rf build/ dist/ *.egg-info .pytest_cache .mypy_cache .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} +

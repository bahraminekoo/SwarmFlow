# Contributing to SwarmFlow

Thanks for your interest in contributing! Here's how to get started.

## Development Setup

```bash
git clone https://github.com/hossein/SwarmFlow.git
cd SwarmFlow
pip install -e ".[dev]"
```

## Running Tests

```bash
make test          # Run tests
make test-cov      # Run tests with coverage
make lint          # Run linter
make format        # Auto-format code
```

## Project Structure

```
src/swarmflow/
├── engine/        # Core: graph, state, scheduler, inbox, templates
├── agents/        # Leader + worker agents
├── dashboard/     # FastAPI + WebSocket real-time UI
├── templates/     # Built-in YAML team templates
├── config.py      # Pydantic configuration
├── models.py      # Data models
├── llm.py         # LLM factory (OpenRouter / Ollama)
└── cli.py         # Typer CLI
```

## Adding a New Template

1. Create a YAML file in `src/swarmflow/templates/your-template.yaml`
2. Follow the schema in existing templates (name, description, workers, default_goal)
3. Add a test in `tests/test_engine/test_templates.py`
4. Test it: `swarmflow launch your-template --goal "Your goal"`

## Code Style

- We use [Ruff](https://docs.astral.sh/ruff/) for linting and formatting
- Type hints are required (enforced by mypy)
- Target Python 3.10+
- Keep line length ≤ 100 characters

## Pull Request Process

1. Fork the repo and create a branch from `main`
2. Add tests for any new functionality
3. Ensure `make lint` and `make test` pass
4. Update documentation if needed
5. Open a PR with a clear description

## Reporting Issues

Use GitHub Issues. Include:
- Python version and OS
- Steps to reproduce
- Expected vs actual behavior
- Error logs (if any)

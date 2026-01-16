.PHONY: install dev run test lint format clean

# Install dependencies
install:
	uv sync

# Install with dev dependencies
dev:
	uv sync --group dev

# Run the orchestrator (default A2A agent at localhost:9999)
run:
	uv run python -m orchestrator

# Run tests
test:
	uv run pytest tests/ -v

# Run tests with coverage
test-cov:
	uv run pytest tests/ -v --cov=src/orchestrator --cov-report=term-missing

# Lint code
lint:
	uv run ruff check src/ tests/
	uv run mypy src/

# Format code
format:
	uv run ruff format src/ tests/
	uv run ruff check --fix src/ tests/

# Clean build artifacts
clean:
	rm -rf __pycache__ .pytest_cache .mypy_cache .ruff_cache
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

# Show help
help:
	@echo "Available targets:"
	@echo "  install       - Install dependencies"
	@echo "  dev           - Install with dev dependencies"
	@echo "  run           - Run the orchestrator"
	@echo "  run-with-agent - Run with A2A agent at localhost:9999"
	@echo "  test          - Run tests"
	@echo "  test-cov      - Run tests with coverage"
	@echo "  lint          - Lint code"
	@echo "  format        - Format code"
	@echo "  clean         - Clean build artifacts"

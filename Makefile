# ==============================================================================
# Makefile for Dynamic MCP Skill Hub development and deployment
# ==============================================================================

.PHONY: install run-mcp run-ui test docker-build docker-run clean help

help:
	@echo "Available commands:"
	@echo "  install      - Install packages and development dependencies in editable mode"
	@echo "  run-mcp      - Start the FastMCP stdio/SSE server"
	@echo "  run-ui       - Start the Reflex development dashboard"
	@echo "  test         - Run the unit testing suite"
	@echo "  docker-build - Build the production Docker image locally"
	@echo "  docker-run   - Start container services using Docker Compose"
	@echo "  clean        - Clean build, test, and python runtime caches"

install:
	pip install -e .[dev]

run-mcp:
	python -m dynamic_mcp_skill_hub.main

run-ui:
	reflex run

test:
	pytest tests/

docker-build:
	docker build -t dynamic-mcp-skill-hub:latest .

docker-run:
	docker compose up --build -d

clean:
	@echo "Cleaning cache and build files..."
	python -c "import shutil, pathlib; [shutil.rmtree(p) for p in pathlib.Path('.').rglob('__pycache__')]"
	python -c "import shutil, pathlib; [shutil.rmtree(p) for p in pathlib.Path('.').rglob('.pytest_cache')]"
	python -c "import shutil, pathlib; [shutil.rmtree(p) for p in pathlib.Path('.').rglob('.web')]"
	python -c "import shutil, pathlib; [shutil.rmtree(p) for p in pathlib.Path('.').rglob('.reflex')]"
	python -c "import shutil, pathlib; [shutil.rmtree(p) for p in pathlib.Path('.').rglob('*.egg-info')]"
	python -c "import shutil, pathlib; [p.unlink() for p in pathlib.Path('.').rglob('*.pyc')]"

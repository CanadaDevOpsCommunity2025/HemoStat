.PHONY: help install dev format lint typecheck quality test clean docker-up docker-down docker-logs docs-install docs-build docs-clean docs-serve docs-check docs windows windows-build windows-up windows-down windows-logs windows-test linux linux-build linux-up linux-down linux-logs linux-test macos macos-build macos-up macos-down macos-logs macos-test

help:
	@echo "HemoStat Development Commands"
	@echo "============================="
	@echo ""
	@echo "Setup:"
	@echo "  make install          Install all dependencies"
	@echo "  make dev              Install dev dependencies"
	@echo ""
	@echo "Code Quality:"
	@echo "  make format           Format code with ruff"
	@echo "  make lint             Lint code with ruff and auto-fix"
	@echo "  make typecheck        Run type checker (ty)"
	@echo "  make quality          Run all quality checks (format, lint, typecheck)"
	@echo ""
	@echo "Testing:"
	@echo "  make test             Run all tests"
	@echo "  make test-cov         Run tests with coverage report"
	@echo ""
	@echo "Docker (Generic):"
	@echo "  make docker-build     Build Docker images"
	@echo "  make docker-up        Start all services"
	@echo "  make docker-down      Stop all services"
	@echo "  make docker-logs      View service logs"
	@echo "  make docker-clean     Stop and remove volumes"
	@echo ""
	@echo "Platform-Specific Docker:"
	@echo "  make windows          Build and run for Windows"
	@echo "  make windows-build    Build for Windows"
	@echo "  make windows-up       Start Windows services"
	@echo "  make windows-down     Stop Windows services"
	@echo "  make windows-logs     View Windows logs"
	@echo "  make windows-test     Start Windows with test containers"
	@echo "  make linux            Build and run for Linux"
	@echo "  make linux-build      Build for Linux"
	@echo "  make linux-up         Start Linux services"
	@echo "  make linux-down       Stop Linux services"
	@echo "  make linux-logs       View Linux logs"
	@echo "  make linux-test       Start Linux with test containers"
	@echo "  make macos            Build and run for macOS"
	@echo "  make macos-build      Build for macOS"
	@echo "  make macos-up         Start macOS services"
	@echo "  make macos-down       Stop macOS services"
	@echo "  make macos-logs       View macOS logs"
	@echo "  make macos-test       Start macOS with test containers"
	@echo ""
	@echo "Agents:"
	@echo "  make monitor          Run Monitor Agent locally"
	@echo "  make analyzer         Run Analyzer Agent locally"
	@echo "  make responder        Run Responder Agent locally"
	@echo "  make alert            Run Alert Agent locally"
	@echo ""
	@echo "Documentation:"
	@echo "  make docs-install     Install documentation dependencies"
	@echo "  make docs-build       Build Sphinx documentation into /docs"
	@echo "  make docs-clean       Clean documentation build artifacts"
	@echo "  make docs-serve       Build and serve documentation locally"
	@echo "  make docs-check       Build docs with warnings as errors"
	@echo "  make docs             Alias for docs-build"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean            Remove build artifacts and cache"
	@echo ""

# Setup & Installation
install:
	uv sync --all-extras

dev:
	uv sync

# Code Quality
format:
	ruff format

lint:
	ruff check --fix

typecheck:
	ty check

quality: format lint typecheck
	@echo "✓ All quality checks passed!"

# Testing
test:
	pytest

test-cov:
	pytest --cov=agents --cov-report=html --cov-report=term-missing
	@echo "Coverage report generated in htmlcov/index.html"

# Docker Operations
docker-build:
	docker-compose build

docker-up:
	docker-compose up -d
	@echo "✓ Services started"
	@echo "  Monitor:   docker-compose logs -f monitor"
	@echo "  Analyzer:  docker-compose logs -f analyzer"
	@echo "  Responder: docker-compose logs -f responder"
	@echo "  Alert:     docker-compose logs -f alert"

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

docker-clean:
	docker-compose down -v

# Platform-Specific Docker Operations

# Windows
windows: windows-build windows-up
	@echo "✓ Windows services built and started"
	@echo "  Dashboard: http://localhost:8501"
	@echo "  Test API:  http://localhost:5000"

windows-build:
	docker compose -f docker-compose.yml -f docker-compose.windows.yml --env-file .env.docker.windows build

windows-up:
	docker compose -f docker-compose.yml -f docker-compose.windows.yml --env-file .env.docker.windows up -d
	@echo "✓ Windows services started"

windows-down:
	docker compose -f docker-compose.yml -f docker-compose.windows.yml down

windows-logs:
	docker compose -f docker-compose.yml -f docker-compose.windows.yml logs -f

windows-test:
	docker compose -f docker-compose.yml -f docker-compose.windows.yml -f docker-compose.test.yml --env-file .env.docker.windows up -d
	@echo "✓ Windows services + test containers started"
	@echo "  Dashboard: http://localhost:8501"
	@echo "  Test containers: test-crash-loop, test-cpu-stress, test-memory-stress, etc."
	@echo "  See TESTING.md for details"

# Linux
linux: linux-build linux-up
	@echo "✓ Linux services built and started"
	@echo "  Dashboard: http://localhost:8501"
	@echo "  Test API:  http://localhost:5000"

linux-build:
	docker compose -f docker-compose.yml -f docker-compose.linux.yml --env-file .env.docker.linux build

linux-up:
	docker compose -f docker-compose.yml -f docker-compose.linux.yml --env-file .env.docker.linux up -d
	@echo "✓ Linux services started"

linux-down:
	docker compose -f docker-compose.yml -f docker-compose.linux.yml down

linux-logs:
	docker compose -f docker-compose.yml -f docker-compose.linux.yml logs -f

linux-test:
	docker compose -f docker-compose.yml -f docker-compose.linux.yml -f docker-compose.test.yml --env-file .env.docker.linux up -d
	@echo "✓ Linux services + test containers started"
	@echo "  Dashboard: http://localhost:8501"
	@echo "  Test containers: test-crash-loop, test-cpu-stress, test-memory-stress, etc."
	@echo "  See TESTING.md for details"

# macOS
macos: macos-build macos-up
	@echo "✓ macOS services built and started"
	@echo "  Dashboard: http://localhost:8501"
	@echo "  Test API:  http://localhost:5000"

macos-build:
	docker compose -f docker-compose.yml -f docker-compose.macos.yml --env-file .env.docker.macos build

macos-up:
	docker compose -f docker-compose.yml -f docker-compose.macos.yml --env-file .env.docker.macos up -d
	@echo "✓ macOS services started"

macos-down:
	docker compose -f docker-compose.yml -f docker-compose.macos.yml down

macos-logs:
	docker compose -f docker-compose.yml -f docker-compose.macos.yml logs -f

macos-test:
	docker compose -f docker-compose.yml -f docker-compose.macos.yml -f docker-compose.test.yml --env-file .env.docker.macos up -d
	@echo "✓ macOS services + test containers started"
	@echo "  Dashboard: http://localhost:8501"
	@echo "  Test containers: test-crash-loop, test-cpu-stress, test-memory-stress, etc."
	@echo "  See TESTING.md for details"

# Local Agent Running
monitor:
	python -m agents.hemostat_monitor.main

analyzer:
	python -m agents.hemostat_analyzer.main

responder:
	python -m agents.hemostat_responder.main

alert:
	python -m agents.hemostat_alert.main

# Documentation
docs-install:
	uv sync --extra docs

docs-build:
	sphinx-build -b html docs/source docs

docs-clean:
	rm -rf docs/*.html docs/*.js docs/_static docs/_sources docs/_modules docs/.buildinfo docs/objects.inv docs/searchindex.js docs/source/_autosummary

docs-serve: docs-build
	python -m http.server -d docs 8000

docs-check:
	sphinx-build -b html docs/source docs -W --keep-going

docs: docs-build

# Maintenance
clean:
	rm -rf build/ dist/ *.egg-info
	rm -rf .pytest_cache/ .mypy_cache/ .ruff_cache/
	rm -rf htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	@echo "✓ Cleaned up build artifacts and cache"

.DEFAULT_GOAL := help

.PHONY: help install dev format lint typecheck quality test clean docker-up docker-down docker-logs

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
	@echo "Docker:"
	@echo "  make docker-build     Build Docker images"
	@echo "  make docker-up        Start all services"
	@echo "  make docker-down      Stop all services"
	@echo "  make docker-logs      View service logs"
	@echo "  make docker-clean     Stop and remove volumes"
	@echo ""
	@echo "Agents:"
	@echo "  make monitor          Run Monitor Agent locally"
	@echo "  make analyzer         Run Analyzer Agent locally"
	@echo "  make responder        Run Responder Agent locally"
	@echo "  make alert            Run Alert Agent locally"
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

# Local Agent Running
monitor:
	python -m agents.hemostat_monitor.main

analyzer:
	python -m agents.hemostat_analyzer.main

responder:
	python -m agents.hemostat_responder.main

alert:
	python -m agents.hemostat_alert.main

# Maintenance
clean:
	rm -rf build/ dist/ *.egg-info
	rm -rf .pytest_cache/ .mypy_cache/ .ruff_cache/
	rm -rf htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	@echo "✓ Cleaned up build artifacts and cache"

.DEFAULT_GOAL := help

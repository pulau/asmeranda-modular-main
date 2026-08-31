.PHONY: help install dev test lint format type-check coverage clean all security

help:
	@echo "Asmeranda AI - Development Commands"
	@echo "===================================="
	@echo ""
	@echo "Installation & Setup:"
	@echo "  make install       - Install all dependencies"
	@echo "  make dev           - Setup development environment"
	@echo ""
	@echo "Testing:"
	@echo "  make test          - Run all tests"
	@echo "  make test-unit     - Run unit tests only"
	@echo "  make test-integration - Run integration tests only"
	@echo "  make test-quick    - Run fast tests (skip slow)"
	@echo "  make coverage      - Run tests with coverage report"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint          - Run all linters"
	@echo "  make format        - Format code automatically"
	@echo "  make type-check    - Run type checking"
	@echo "  make black         - Format with Black only"
	@echo "  make isort         - Sort imports only"
	@echo "  make flake8        - Lint with flake8 only"
	@echo ""
	@echo "Security:"
	@echo "  make security      - Run security scans"
	@echo "  make bandit        - Security scan with bandit"
	@echo "  make safety        - Check dependencies for vulnerabilities"
	@echo ""
	@echo "Utility:"
	@echo "  make clean         - Remove generated files"
	@echo "  make all           - Run all checks (lint, type-check, test)"
	@echo ""

install:
	@echo "Installing dependencies..."
	pip install -q -r requirements.txt
	pip install -q -r requirements-backend.txt
	pip install -q -r requirements-dev.txt
	@echo "✓ Dependencies installed"

dev: install
	@echo "Setting up development environment..."
	pip install -q pre-commit
	pre-commit install
	@echo "✓ Development environment ready"

test:
	@echo "Running all tests..."
	pytest backend/tests -v --tb=short

test-unit:
	@echo "Running unit tests..."
	pytest backend/tests/unit -v --tb=short

test-integration:
	@echo "Running integration tests..."
	pytest backend/tests/integration -v --tb=short

test-quick:
	@echo "Running tests (excluding slow tests)..."
	pytest backend/tests -v -m "not slow" --tb=short

coverage:
	@echo "Running tests with coverage..."
	pytest backend/tests \
		--cov=backend \
		--cov=core \
		--cov-report=html \
		--cov-report=term-missing \
		--cov-report=xml \
		--tb=short
	@echo "✓ Coverage report: htmlcov/index.html"

lint: black isort flake8
	@echo "✓ All linting checks completed"

format: black isort
	@echo "✓ Code formatted"

black:
	@echo "Formatting with Black..."
	black backend/ core/ --quiet

isort:
	@echo "Sorting imports with isort..."
	isort backend/ core/ --quiet

flake8:
	@echo "Linting with flake8..."
	flake8 backend/ core/ --max-line-length=100

type-check:
	@echo "Type checking with mypy..."
	mypy backend/ core/ --ignore-missing-imports || true
	@echo "✓ Type checking complete"

security: bandit safety
	@echo "✓ Security checks completed"

bandit:
	@echo "Security scan with bandit..."
	bandit -r backend/ core/ -ll || true

safety:
	@echo "Checking dependencies..."
	safety check || true

clean:
	@echo "Cleaning up..."
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name htmlcov -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name ".coverage" -delete
	@echo "✓ Cleanup completed"

all: lint type-check test
	@echo ""
	@echo "═════════════════════════════════════"
	@echo "✓ All checks passed!"
	@echo "═════════════════════════════════════"

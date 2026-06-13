.PHONY: help install test test-cov test-fast test-async smoke-test clean lint format run deps-check docker-build docker-run

help:
	@echo "AI Job Search Agent - Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make install         - Install all dependencies"
	@echo "  make deps-check      - Check for outdated dependencies"
	@echo ""
	@echo "Development:"
	@echo "  make run             - Run the Streamlit app locally"
	@echo "  make lint            - Run code quality checks"
	@echo "  make format          - Auto-format code with black and isort"
	@echo ""
	@echo "Testing:"
	@echo "  make test            - Run all tests with coverage"
	@echo "  make test-fast       - Run tests without network tests"
	@echo "  make test-async      - Run only async tests"
	@echo "  make test-cov        - Run tests and generate HTML coverage report"
	@echo "  make smoke-test      - Run smoke test"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-build    - Build Docker image"
	@echo "  make docker-run      - Run Docker container locally"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean           - Clean up generated files and cache"

install:
	pip install -r requirements.txt

deps-check:
	pip list --outdated

run:
	streamlit run app.py

test:
	pytest -v --cov=. --cov-report=html --cov-report=term

test-fast:
	pytest -v -m "not network"

test-async:
	pytest -v -m asyncio

test-cov:
	pytest --cov=. --cov-report=html --cov-report=term
	@echo "Coverage report generated in htmlcov/index.html"

smoke-test:
	python smoke_test.py

lint:
	flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
	mypy . --ignore-missing-imports
	@echo "Code quality checks passed!"

format:
	black .
	isort .

clean:
	find . -type f -name '*.pyc' -delete
	find . -type d -name '__pycache__' -delete
	find . -type d -name '.pytest_cache' -delete
	find . -type d -name '.mypy_cache' -delete
	find . -type d -name 'htmlcov' -delete
	find . -type f -name '.coverage' -delete
	find . -type f -name '*.egg-info' -delete

docker-build:
	docker build -t job-search-agent:latest .

docker-run:
	docker run -p 8501:8501 --env-file .env job-search-agent:latest

.DEFAULT_GOAL := help
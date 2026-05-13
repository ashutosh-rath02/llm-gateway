# LLM Gateway

Production-oriented gateway scaffold for standardized LLM execution, routing, validation, tracing, and eval workflows.

## Current Status

This repository currently includes:

- FastAPI service scaffold
- request trace middleware
- health endpoint
- mocked `POST /v1/llm/execute` endpoint
- configuration system
- SQLAlchemy and Alembic scaffolding
- Docker Compose for Postgres and Redis
- starter tests

## Quick Start

1. Create a virtual environment and install dependencies from `pyproject.toml`.
2. Copy `.env.example` to `.env`.
3. Start local infra with `docker-compose up -d`.
4. Run the API with `uvicorn app.main:app --reload`.
5. Run tests with `pytest`.

## API Endpoints

- `GET /healthz`
- `GET /v1/meta`
- `POST /v1/llm/execute`


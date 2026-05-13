# Changelog

## 0.1.0 - 2026-05-13

Initial scaffold for the LLM Gateway MVP.

### Added

- FastAPI application scaffold with a production-shaped `app/` layout
- Request trace middleware with `X-Trace-Id` and request timing headers
- `GET /healthz` and `GET /v1/meta` endpoints
- Mocked `POST /v1/llm/execute` endpoint with normalized request and response schemas
- Deterministic mock provider for plain-text and structured-output flows
- JSON Schema validation service for structured outputs
- Configuration management via environment variables and `.env.example`
- SQLAlchemy and Alembic scaffolding for future trace persistence
- Redis worker placeholder for async trace/background processing
- Local development infrastructure via `docker-compose.yml` for Postgres and Redis
- Pytest-based starter test suite covering health and execute flows

### Notes

- The OpenAI-compatible provider interface is scaffolded but not yet implemented.
- Internal planning documents are intentionally not part of the publishable project set.

# Changelog

## Unreleased

### Added

- OpenAI-compatible provider implementation using the Responses API
- Optional request-level provider override for testing `mock` and `openai_compatible`
- Trace persistence service with trace and model-call records
- Initial Alembic migration for persisted trace tables
- Provider parser tests and trace persistence tests

### Changed

- Cost calculation now uses model-specific pricing metadata for known models
- Test setup now uses an isolated SQLite database so persistence is exercised in CI-friendly runs
- README now documents migrations and live OpenAI provider testing
- The bundled Postgres dev port now defaults to `5433` to avoid collisions with local Postgres services
- Outbound OpenAI structured-output schemas are normalized to satisfy strict-mode requirements such as `additionalProperties: false`
- Trace persistence now flushes parent trace rows before model-call inserts, fixing foreign-key write failures discovered in live testing

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

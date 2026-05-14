# Changelog

## Unreleased

### Added

- Optional API-key authentication with tenant-scoped access control for execute, trace, metrics, and eval endpoints
- Feature allowlists for API keys so gateway access can be constrained per caller integration
- Configurable execute rate limiting and request budget caps for safer shared usage
- Configurable trace-storage deny lists and recursive metadata redaction for safer persisted traces
- Lightweight internal dashboard for metrics, recent traces, and trace lookup
- OpenAI-compatible provider implementation using the Responses API
- Optional request-level provider override for testing `mock` and `openai_compatible`
- Rule-based model routing for `cost_optimized`, `balanced`, `quality_optimized`, and explicit model selection
- Fallback to stronger models when provider errors or validation failures occur within request budgets
- Trace persistence service with trace and model-call records
- Initial Alembic migration for persisted trace tables
- Provider parser tests and trace persistence tests
- Trace detail endpoint at `GET /v1/traces/{trace_id}`
- Cost metrics endpoint at `GET /v1/metrics/cost`
- Prompt template name/version tracking on execute requests and persisted traces
- Same-model repair retry for structured-output validation failures
- Reliability metrics endpoint at `GET /v1/metrics/reliability`
- Eval export endpoint at `POST /v1/evals/export`
- Lightweight eval CLI for exporting, summarizing, and comparing JSONL datasets

### Changed

- README and `.env.example` now document copy-paste-safe auth configuration for local testing
- Tests now reset auth and rate-limit state so local developer `.env` settings do not leak into the suite
- Trace persistence now redacts sensitive metadata keys and can skip prompt/output previews for specific features
- The dashboard is intentionally thin and reuses the protected gateway APIs instead of introducing a separate data path
- Cost calculation now uses model-specific pricing metadata for known models
- Trace model-call records now label attempts as `primary`, `repair`, or `fallback`
- Cost metrics filters now also support prompt template name/version, and README flowcharts now cover reliability rollups
- README flowcharts now cover eval export, and trace filters are reusable across metrics and export paths
- Test setup now uses an isolated SQLite database so persistence is exercised in CI-friendly runs
- README now includes living Mermaid flowcharts for request execution, repair, trace persistence, and reliability metrics
- The bundled Postgres dev port now defaults to `5433` to avoid collisions with local Postgres services
- Outbound OpenAI structured-output schemas are normalized to satisfy strict-mode requirements such as `additionalProperties: false`
- Trace persistence now flushes parent trace rows before model-call inserts, fixing foreign-key write failures discovered in live testing
- Unused Redis and worker-placeholder scaffold code was removed until background processing is actually introduced
- Cost calculation now resolves dated OpenAI model IDs like `gpt-5.4-mini-2026-03-17` back to their pricing aliases

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

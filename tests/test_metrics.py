from fastapi.testclient import TestClient

from app.db.session import get_session_factory
from app.models.trace import ModelCallRecord, TraceRecord


def seed_trace_records() -> None:
    session = get_session_factory()()
    try:
        session.add_all(
            [
                TraceRecord(
                    trace_id="trace_success_primary",
                    feature="support_triage",
                    task_type="faq",
                    routing_policy="balanced",
                    risk_level="low",
                    status="success",
                    provider="mock",
                    model="mock-fast-small",
                    prompt_template_name="support_prompt",
                    prompt_template_version="v1",
                    tenant_id="tenant_123",
                    request_metadata={},
                    input_tokens=10,
                    output_tokens=5,
                    latency_ms=100,
                    cost_usd=0.001,
                    fallback_used=False,
                    fallback_level=0,
                ),
                TraceRecord(
                    trace_id="trace_repair_recovered",
                    feature="support_triage",
                    task_type="structured_extraction",
                    routing_policy="cost_optimized",
                    risk_level="low",
                    status="success",
                    provider="openai_compatible",
                    model="gpt-5-nano",
                    prompt_template_name="support_prompt",
                    prompt_template_version="v2",
                    tenant_id="tenant_123",
                    request_metadata={},
                    input_tokens=22,
                    output_tokens=8,
                    latency_ms=240,
                    cost_usd=0.002,
                    schema_valid=True,
                    fallback_used=False,
                    fallback_level=0,
                ),
                TraceRecord(
                    trace_id="trace_fallback_success",
                    feature="invoice_extraction",
                    task_type="structured_extraction",
                    routing_policy="cost_optimized",
                    risk_level="medium",
                    status="success",
                    provider="openai_compatible",
                    model="gpt-5-mini",
                    prompt_template_name="invoice_prompt",
                    prompt_template_version="v1",
                    tenant_id="tenant_456",
                    request_metadata={},
                    input_tokens=30,
                    output_tokens=12,
                    latency_ms=420,
                    cost_usd=0.004,
                    schema_valid=True,
                    fallback_used=True,
                    fallback_level=1,
                ),
                TraceRecord(
                    trace_id="trace_provider_error",
                    feature="invoice_extraction",
                    task_type="faq",
                    routing_policy="cost_optimized",
                    risk_level="low",
                    status="provider_error",
                    provider="openai_compatible",
                    model="gpt-5-nano",
                    error_type="provider_timeout",
                    prompt_template_name="invoice_prompt",
                    prompt_template_version="v1",
                    tenant_id="tenant_456",
                    request_metadata={},
                    latency_ms=200,
                    cost_usd=0.0,
                    fallback_used=False,
                    fallback_level=0,
                ),
                TraceRecord(
                    trace_id="trace_validation_failed",
                    feature="policy_review",
                    task_type="structured_extraction",
                    routing_policy="explicit_model",
                    risk_level="high",
                    status="validation_failed",
                    provider="openai_compatible",
                    model="gpt-5-nano",
                    prompt_template_name="review_prompt",
                    prompt_template_version="v1",
                    tenant_id="tenant_789",
                    request_metadata={},
                    input_tokens=24,
                    output_tokens=7,
                    latency_ms=300,
                    cost_usd=0.0025,
                    schema_valid=False,
                    fallback_used=False,
                    fallback_level=0,
                ),
            ]
        )
        session.flush()
        session.add_all(
            [
                ModelCallRecord(
                    trace_id="trace_success_primary",
                    attempt=1,
                    attempt_kind="primary",
                    provider="mock",
                    model="mock-fast-small",
                    status="success",
                    input_tokens=10,
                    output_tokens=5,
                    latency_ms=100,
                    cost_usd=0.001,
                ),
                ModelCallRecord(
                    trace_id="trace_repair_recovered",
                    attempt=1,
                    attempt_kind="primary",
                    provider="openai_compatible",
                    model="gpt-5-nano",
                    status="validation_failed",
                    input_tokens=11,
                    output_tokens=4,
                    latency_ms=120,
                    cost_usd=0.001,
                ),
                ModelCallRecord(
                    trace_id="trace_repair_recovered",
                    attempt=2,
                    attempt_kind="repair",
                    provider="openai_compatible",
                    model="gpt-5-nano",
                    status="success",
                    input_tokens=11,
                    output_tokens=4,
                    latency_ms=120,
                    cost_usd=0.001,
                ),
                ModelCallRecord(
                    trace_id="trace_fallback_success",
                    attempt=1,
                    attempt_kind="primary",
                    provider="openai_compatible",
                    model="gpt-5-nano",
                    status="provider_error",
                    error_type="provider_error",
                    latency_ms=90,
                    cost_usd=0.0,
                ),
                ModelCallRecord(
                    trace_id="trace_fallback_success",
                    attempt=2,
                    attempt_kind="fallback",
                    provider="openai_compatible",
                    model="gpt-5-mini",
                    status="success",
                    input_tokens=30,
                    output_tokens=12,
                    latency_ms=330,
                    cost_usd=0.004,
                ),
                ModelCallRecord(
                    trace_id="trace_provider_error",
                    attempt=1,
                    attempt_kind="primary",
                    provider="openai_compatible",
                    model="gpt-5-nano",
                    status="provider_error",
                    error_type="provider_timeout",
                    latency_ms=200,
                    cost_usd=0.0,
                ),
                ModelCallRecord(
                    trace_id="trace_validation_failed",
                    attempt=1,
                    attempt_kind="primary",
                    provider="openai_compatible",
                    model="gpt-5-nano",
                    status="validation_failed",
                    input_tokens=12,
                    output_tokens=3,
                    latency_ms=150,
                    cost_usd=0.00125,
                ),
                ModelCallRecord(
                    trace_id="trace_validation_failed",
                    attempt=2,
                    attempt_kind="repair",
                    provider="openai_compatible",
                    model="gpt-5-nano",
                    status="validation_failed",
                    input_tokens=12,
                    output_tokens=4,
                    latency_ms=150,
                    cost_usd=0.00125,
                ),
            ]
        )
        session.commit()
    finally:
        session.close()


def test_cost_metrics_returns_rollups(client: TestClient) -> None:
    payloads = [
        {
            "feature": "support_triage",
            "task_type": "faq",
            "input": "How do I reset my device Wi-Fi?",
            "metadata": {
                "tenant_id": "tenant_123",
                "user_id": "user_1",
            },
        },
        {
            "feature": "invoice_extraction",
            "task_type": "structured_extraction",
            "input": "Invoice INV-001 total is 1250 USD.",
            "schema": {
                "type": "object",
                "properties": {
                    "invoice_number": {"type": "string"},
                    "total": {"type": "number"},
                    "currency": {"type": "string", "enum": ["USD", "EUR"]},
                },
                "required": ["invoice_number", "total", "currency"],
            },
            "metadata": {
                "tenant_id": "tenant_456",
                "user_id": "user_2",
            },
        },
    ]

    for payload in payloads:
        response = client.post("/v1/llm/execute", json=payload)
        assert response.status_code == 200

    response = client.get("/v1/metrics/cost")
    body = response.json()

    assert response.status_code == 200
    assert body["request_count"] == 2
    assert body["success_count"] == 2
    assert body["failed_count"] == 0
    assert body["total_cost_usd"] > 0
    assert {item["key"] for item in body["by_feature"]} == {
        "support_triage",
        "invoice_extraction",
    }
    assert {item["key"] for item in body["by_tenant"]} == {
        "tenant_123",
        "tenant_456",
    }


def test_cost_metrics_supports_feature_filter(client: TestClient) -> None:
    client.post(
        "/v1/llm/execute",
        json={
            "feature": "support_triage",
            "task_type": "faq",
            "input": "How do I reset my device Wi-Fi?",
        },
    )
    client.post(
        "/v1/llm/execute",
        json={
            "feature": "invoice_extraction",
            "task_type": "faq",
            "input": "Extract the invoice total.",
        },
    )

    response = client.get("/v1/metrics/cost?feature=support_triage")
    body = response.json()

    assert response.status_code == 200
    assert body["request_count"] == 1
    assert body["by_feature"][0]["key"] == "support_triage"


def test_reliability_metrics_returns_expected_rollups(client: TestClient) -> None:
    seed_trace_records()

    response = client.get("/v1/metrics/reliability")
    body = response.json()

    assert response.status_code == 200
    assert body["request_count"] == 5
    assert body["success_count"] == 3
    assert body["validation_failed_count"] == 1
    assert body["provider_error_count"] == 1
    assert body["fallback_count"] == 1
    assert body["repair_attempted_count"] == 2
    assert body["repair_recovered_count"] == 1
    assert body["success_rate"] == 0.6
    assert body["repair_recovery_rate"] == 0.5
    assert body["avg_attempt_count"] == 1.6
    assert {item["key"] for item in body["by_prompt_template"]} == {
        "support_prompt@v1",
        "support_prompt@v2",
        "invoice_prompt@v1",
        "review_prompt@v1",
    }


def test_reliability_metrics_support_prompt_filters(client: TestClient) -> None:
    seed_trace_records()

    response = client.get(
        "/v1/metrics/reliability"
        "?prompt_template_name=support_prompt&prompt_template_version=v2"
    )
    body = response.json()

    assert response.status_code == 200
    assert body["request_count"] == 1
    assert body["success_count"] == 1
    assert body["repair_attempted_count"] == 1
    assert body["repair_recovered_count"] == 1
    assert body["by_feature"][0]["key"] == "support_triage"

from app.db.session import get_session_factory
from app.evals.runner import compare_eval_summaries, summarize_eval_dataset
from app.models.trace import ModelCallRecord, TraceRecord


def test_export_eval_dataset_returns_filtered_items(client) -> None:
    session = get_session_factory()()
    try:
        session.add(
            TraceRecord(
                trace_id="trace_export_1",
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
                user_id_hash="hash_123",
                request_metadata={"source": "test"},
                input_preview="How do I reset my device Wi-Fi?",
                output_preview="Mock support answer",
                input_tokens=10,
                output_tokens=5,
                latency_ms=100,
                cost_usd=0.001,
                fallback_used=False,
                fallback_level=0,
            )
        )
        session.flush()
        session.add(
            ModelCallRecord(
                trace_id="trace_export_1",
                attempt=1,
                attempt_kind="primary",
                provider="mock",
                model="mock-fast-small",
                status="success",
                input_tokens=10,
                output_tokens=5,
                latency_ms=100,
                cost_usd=0.001,
            )
        )
        session.commit()
    finally:
        session.close()

    response = client.post(
        "/v1/evals/export",
        json={
            "feature": "support_triage",
            "prompt_template_name": "support_prompt",
            "prompt_template_version": "v1",
        },
    )
    body = response.json()

    assert response.status_code == 200
    assert body["item_count"] == 1
    assert body["items"][0]["feature"] == "support_triage"
    assert body["items"][0]["prompt_template_name"] == "support_prompt"
    assert body["items"][0]["prompt_template_version"] == "v1"
    assert body["items"][0]["input"] == "How do I reset my device Wi-Fi?"
    assert body["items"][0]["output"] == "Mock support answer"
    assert len(body["items"][0]["model_calls"]) == 1


def test_eval_runner_summarizes_and_compares_datasets() -> None:
    baseline_items = [
        {
            "status": "success",
            "schema_valid": True,
            "fallback": {"used": False},
            "latency_ms": 100,
            "cost_usd": 0.01,
        },
        {
            "status": "validation_failed",
            "schema_valid": False,
            "fallback": {"used": True},
            "latency_ms": 200,
            "cost_usd": 0.02,
        },
    ]
    candidate_items = [
        {
            "status": "success",
            "schema_valid": True,
            "fallback": {"used": False},
            "latency_ms": 90,
            "cost_usd": 0.009,
        },
        {
            "status": "success",
            "schema_valid": True,
            "fallback": {"used": False},
            "latency_ms": 110,
            "cost_usd": 0.011,
        },
    ]

    baseline = summarize_eval_dataset(baseline_items)
    candidate = summarize_eval_dataset(candidate_items)
    comparison = compare_eval_summaries(baseline, candidate)

    assert baseline.success_rate == 0.5
    assert baseline.validation_failure_rate == 0.5
    assert baseline.fallback_rate == 0.5
    assert candidate.success_rate == 1.0
    assert candidate.avg_latency_ms == 100.0
    assert comparison["success_rate"]["delta"] == 0.5
    assert comparison["validation_failure_rate"]["delta"] == -0.5

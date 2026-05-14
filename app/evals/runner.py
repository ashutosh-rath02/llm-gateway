from dataclasses import asdict, dataclass
from typing import Any


@dataclass(slots=True)
class EvalSummary:
    item_count: int
    success_rate: float
    validation_failure_rate: float
    provider_error_rate: float
    schema_valid_rate: float
    fallback_rate: float
    avg_latency_ms: float
    avg_cost_usd: float


def summarize_eval_dataset(items: list[dict[str, Any]]) -> EvalSummary:
    item_count = len(items)
    success_count = sum(1 for item in items if item.get("status") == "success")
    validation_failed_count = sum(
        1 for item in items if item.get("status") == "validation_failed"
    )
    provider_error_count = sum(
        1 for item in items if item.get("status") == "provider_error"
    )
    schema_checked = [item for item in items if item.get("schema_valid") is not None]
    schema_valid_count = sum(1 for item in schema_checked if item.get("schema_valid") is True)
    fallback_count = sum(
        1 for item in items if (item.get("fallback") or {}).get("used") is True
    )
    total_latency_ms = sum(int(item.get("latency_ms") or 0) for item in items)
    total_cost_usd = sum(float(item.get("cost_usd") or 0.0) for item in items)

    return EvalSummary(
        item_count=item_count,
        success_rate=_rate(success_count, item_count),
        validation_failure_rate=_rate(validation_failed_count, item_count),
        provider_error_rate=_rate(provider_error_count, item_count),
        schema_valid_rate=_rate(schema_valid_count, len(schema_checked)),
        fallback_rate=_rate(fallback_count, item_count),
        avg_latency_ms=_average(total_latency_ms, item_count),
        avg_cost_usd=round(_average(total_cost_usd, item_count), 6),
    )


def compare_eval_summaries(
    baseline: EvalSummary,
    candidate: EvalSummary,
) -> dict[str, dict[str, float]]:
    baseline_data = asdict(baseline)
    candidate_data = asdict(candidate)
    keys = [
        "success_rate",
        "validation_failure_rate",
        "provider_error_rate",
        "schema_valid_rate",
        "fallback_rate",
        "avg_latency_ms",
        "avg_cost_usd",
    ]
    return {
        key: {
            "baseline": float(baseline_data[key]),
            "candidate": float(candidate_data[key]),
            "delta": round(float(candidate_data[key]) - float(baseline_data[key]), 6),
        }
        for key in keys
    }


def _rate(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return round(numerator / denominator, 4)


def _average(total: float, count: int) -> float:
    if count == 0:
        return 0.0
    return round(total / count, 2)

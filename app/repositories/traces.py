import hashlib
import json
import logging
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from sqlalchemy import case, func, select
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import get_settings
from app.db.session import session_scope
from app.models.trace import ModelCallRecord, TraceRecord
from app.schemas.llm import GatewayExecuteRequest, GatewayExecuteResponse
from app.schemas.trace import (
    CostBreakdownItem,
    CostMetricsResponse,
    ReliabilityBreakdownItem,
    ReliabilityMetricsResponse,
    TraceDetailResponse,
    TraceModelCallResponse,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class PersistedModelCall:
    attempt: int
    attempt_kind: str
    provider: str
    model: str
    status: str
    error_type: str | None
    input_tokens: int
    output_tokens: int
    cached_input_tokens: int
    latency_ms: int
    cost_usd: float


@dataclass(slots=True)
class ReliabilityAccumulator:
    request_count: int = 0
    success_count: int = 0
    validation_failed_count: int = 0
    provider_error_count: int = 0
    fallback_count: int = 0
    repair_attempted_count: int = 0
    repair_recovered_count: int = 0
    total_attempt_count: int = 0

    def add(self, trace_record: TraceRecord, model_calls: list[ModelCallRecord]) -> None:
        self.request_count += 1
        self.total_attempt_count += len(model_calls)

        if trace_record.status == "success":
            self.success_count += 1
        elif trace_record.status == "validation_failed":
            self.validation_failed_count += 1
        elif trace_record.status == "provider_error":
            self.provider_error_count += 1

        if trace_record.fallback_used:
            self.fallback_count += 1

        repair_attempted = any(call.attempt_kind == "repair" for call in model_calls)
        if repair_attempted:
            self.repair_attempted_count += 1
            if trace_record.status == "success" and not trace_record.fallback_used:
                self.repair_recovered_count += 1


class TraceRepository:
    def record_success(
        self,
        *,
        trace_id: str,
        payload: GatewayExecuteRequest,
        provider_name: str,
        response: GatewayExecuteResponse,
        latency_ms: int,
        model_calls: list[PersistedModelCall],
        gateway_metadata: dict | None = None,
    ) -> None:
        settings = get_settings()
        if not settings.trace_persistence_enabled:
            return

        metadata, tenant_id, user_id_hash = self._sanitize_metadata(
            payload.metadata,
            gateway_metadata=gateway_metadata,
        )
        usage = response.usage

        trace_record = TraceRecord(
            trace_id=trace_id,
            feature=payload.feature,
            task_type=payload.task_type,
            routing_policy=payload.routing_policy,
            risk_level=payload.risk_level,
            status=response.status,
            provider=provider_name,
            model=response.model,
            error_type=None,
            prompt_template_name=payload.prompt_template_name,
            prompt_template_version=payload.prompt_template_version,
            tenant_id=tenant_id,
            user_id_hash=user_id_hash,
            request_metadata=metadata,
            input_preview=self._maybe_input_preview(settings, payload.input),
            output_preview=self._maybe_output_preview(settings, response.output),
            input_tokens=usage.input_tokens if usage else 0,
            output_tokens=usage.output_tokens if usage else 0,
            cached_input_tokens=usage.cached_input_tokens if usage else 0,
            latency_ms=latency_ms,
            cost_usd=usage.cost_usd if usage else 0.0,
            schema_valid=response.validation.schema_valid if response.validation else None,
            business_rules_valid=(
                response.validation.business_rules_valid if response.validation else None
            ),
            fallback_used=response.fallback.used,
            fallback_level=response.fallback.level,
        )
        self._persist(trace_record, self._build_call_records(trace_id, model_calls))

    def record_failure(
        self,
        *,
        trace_id: str,
        payload: GatewayExecuteRequest,
        provider_name: str,
        model_name: str | None,
        error_type: str,
        latency_ms: int,
        model_calls: list[PersistedModelCall],
        total_cost_usd: float = 0.0,
        fallback_level: int = 0,
        gateway_metadata: dict | None = None,
    ) -> None:
        settings = get_settings()
        if not settings.trace_persistence_enabled:
            return

        metadata, tenant_id, user_id_hash = self._sanitize_metadata(
            payload.metadata,
            gateway_metadata=gateway_metadata,
        )

        trace_record = TraceRecord(
            trace_id=trace_id,
            feature=payload.feature,
            task_type=payload.task_type,
            routing_policy=payload.routing_policy,
            risk_level=payload.risk_level,
            status="provider_error",
            provider=provider_name,
            model=model_name,
            error_type=error_type,
            prompt_template_name=payload.prompt_template_name,
            prompt_template_version=payload.prompt_template_version,
            tenant_id=tenant_id,
            user_id_hash=user_id_hash,
            request_metadata=metadata,
            input_preview=self._maybe_input_preview(settings, payload.input),
            output_preview=None,
            input_tokens=0,
            output_tokens=0,
            cached_input_tokens=0,
            latency_ms=latency_ms,
            cost_usd=total_cost_usd,
            schema_valid=None,
            business_rules_valid=None,
            fallback_used=fallback_level > 0,
            fallback_level=fallback_level,
        )
        self._persist(trace_record, self._build_call_records(trace_id, model_calls))

    def _persist(self, trace_record: TraceRecord, call_records: list[ModelCallRecord]) -> None:
        try:
            with session_scope() as session:
                session.add(trace_record)
                session.flush()
                session.add_all(call_records)
        except SQLAlchemyError:
            logger.exception("Trace persistence failed for trace_id=%s", trace_record.trace_id)

    def get_trace_detail(self, trace_id: str) -> TraceDetailResponse | None:
        with session_scope() as session:
            trace_record = session.get(TraceRecord, trace_id)
            if trace_record is None:
                return None

            model_calls = session.scalars(
                select(ModelCallRecord)
                .where(ModelCallRecord.trace_id == trace_id)
                .order_by(ModelCallRecord.attempt.asc(), ModelCallRecord.created_at.asc())
            ).all()

        return TraceDetailResponse(
            trace_id=trace_record.trace_id,
            created_at=trace_record.created_at,
            feature=trace_record.feature,
            task_type=trace_record.task_type,
            routing_policy=trace_record.routing_policy,
            risk_level=trace_record.risk_level,
            status=trace_record.status,
            provider=trace_record.provider,
            model=trace_record.model,
            error_type=trace_record.error_type,
            prompt_template_name=trace_record.prompt_template_name,
            prompt_template_version=trace_record.prompt_template_version,
            tenant_id=trace_record.tenant_id,
            user_id_hash=trace_record.user_id_hash,
            request_metadata=trace_record.request_metadata,
            input_preview=trace_record.input_preview,
            output_preview=trace_record.output_preview,
            validation=self._build_validation_summary(trace_record),
            usage=self._build_usage_summary(trace_record),
            fallback=self._build_fallback_summary(trace_record),
            latency_ms=trace_record.latency_ms,
            cost_usd=trace_record.cost_usd,
            model_calls=[
                TraceModelCallResponse(
                    attempt=call.attempt,
                    attempt_kind=call.attempt_kind,
                    provider=call.provider,
                    model=call.model,
                    status=call.status,
                    error_type=call.error_type,
                    usage=self._build_usage_summary(call),
                    latency_ms=call.latency_ms,
                    created_at=call.created_at,
                )
                for call in model_calls
            ],
        )

    def _build_call_records(
        self,
        trace_id: str,
        model_calls: list[PersistedModelCall],
    ) -> list[ModelCallRecord]:
        return [
            ModelCallRecord(
                trace_id=trace_id,
                attempt=call.attempt,
                attempt_kind=call.attempt_kind,
                provider=call.provider,
                model=call.model,
                status=call.status,
                error_type=call.error_type,
                input_tokens=call.input_tokens,
                output_tokens=call.output_tokens,
                cached_input_tokens=call.cached_input_tokens,
                latency_ms=call.latency_ms,
                cost_usd=call.cost_usd,
            )
            for call in model_calls
        ]

    def get_cost_metrics(
        self,
        *,
        feature: str | None = None,
        model: str | None = None,
        tenant_id: str | None = None,
        prompt_template_name: str | None = None,
        prompt_template_version: str | None = None,
    ) -> CostMetricsResponse:
        with session_scope() as session:
            filters = self._build_trace_filters(
                feature=feature,
                model=model,
                tenant_id=tenant_id,
                prompt_template_name=prompt_template_name,
                prompt_template_version=prompt_template_version,
            )
            traces = session.scalars(self._build_trace_query(filters)).all()

            by_feature = self._group_cost_breakdown(session, "feature", filters)
            by_model = self._group_cost_breakdown(session, "model", filters)
            by_tenant = self._group_cost_breakdown(session, "tenant_id", filters)

        request_count = len(traces)
        success_count = sum(1 for trace in traces if trace.status == "success")
        failed_count = request_count - success_count
        total_cost_usd = round(sum(trace.cost_usd for trace in traces), 6)
        avg_cost_usd = round(total_cost_usd / request_count, 6) if request_count else 0.0

        return CostMetricsResponse(
            request_count=request_count,
            success_count=success_count,
            failed_count=failed_count,
            total_cost_usd=total_cost_usd,
            avg_cost_usd=avg_cost_usd,
            by_feature=by_feature,
            by_model=by_model,
            by_tenant=by_tenant,
        )

    def get_reliability_metrics(
        self,
        *,
        feature: str | None = None,
        model: str | None = None,
        tenant_id: str | None = None,
        prompt_template_name: str | None = None,
        prompt_template_version: str | None = None,
    ) -> ReliabilityMetricsResponse:
        with session_scope() as session:
            filters = self._build_trace_filters(
                feature=feature,
                model=model,
                tenant_id=tenant_id,
                prompt_template_name=prompt_template_name,
                prompt_template_version=prompt_template_version,
            )
            traces = session.scalars(self._build_trace_query(filters)).all()
            model_calls_by_trace = self._load_model_calls_by_trace(session, traces)

        overall = self._build_reliability_accumulator(traces, model_calls_by_trace)
        return ReliabilityMetricsResponse(
            request_count=overall.request_count,
            success_count=overall.success_count,
            validation_failed_count=overall.validation_failed_count,
            provider_error_count=overall.provider_error_count,
            fallback_count=overall.fallback_count,
            repair_attempted_count=overall.repair_attempted_count,
            repair_recovered_count=overall.repair_recovered_count,
            success_rate=self._rate(overall.success_count, overall.request_count),
            validation_failure_rate=self._rate(
                overall.validation_failed_count,
                overall.request_count,
            ),
            provider_error_rate=self._rate(
                overall.provider_error_count,
                overall.request_count,
            ),
            fallback_rate=self._rate(overall.fallback_count, overall.request_count),
            repair_attempt_rate=self._rate(
                overall.repair_attempted_count,
                overall.request_count,
            ),
            repair_recovery_rate=self._rate(
                overall.repair_recovered_count,
                overall.repair_attempted_count,
            ),
            avg_attempt_count=self._average_attempt_count(overall),
            by_feature=self._build_reliability_breakdown(
                traces,
                model_calls_by_trace,
                key_fn=lambda trace: trace.feature,
            ),
            by_model=self._build_reliability_breakdown(
                traces,
                model_calls_by_trace,
                key_fn=lambda trace: trace.model or "unknown",
            ),
            by_tenant=self._build_reliability_breakdown(
                traces,
                model_calls_by_trace,
                key_fn=lambda trace: trace.tenant_id or "unknown",
            ),
            by_prompt_template=self._build_reliability_breakdown(
                traces,
                model_calls_by_trace,
                key_fn=self._prompt_template_key,
            ),
        )

    def _sanitize_metadata(
        self,
        metadata: dict[str, Any],
        *,
        gateway_metadata: dict | None = None,
    ) -> tuple[dict[str, Any], str | None, str | None]:
        settings = get_settings()
        sanitized = dict(metadata)
        tenant_id = sanitized.get("tenant_id")
        raw_user_id = sanitized.pop("user_id", None)
        user_id_hash = None

        if raw_user_id is not None:
            user_id_hash = self._hash_identifier(str(raw_user_id))
            if not settings.hash_user_ids:
                sanitized["user_id"] = raw_user_id

        if gateway_metadata:
            sanitized["_gateway"] = gateway_metadata

        return sanitized, tenant_id, user_id_hash

    def _maybe_input_preview(self, settings, prompt: str) -> str | None:
        if not settings.store_prompts:
            return None
        return prompt

    def _maybe_output_preview(self, settings, output: object) -> str | None:
        if not settings.store_outputs:
            return None

        if isinstance(output, str):
            return output

        try:
            return json.dumps(output)
        except TypeError:
            return str(output)

    def _hash_identifier(self, raw_value: str) -> str:
        return hashlib.sha256(raw_value.encode("utf-8")).hexdigest()

    def _group_cost_breakdown(
        self,
        session,
        column_name: str,
        filters: list,
    ) -> list[CostBreakdownItem]:
        column = getattr(TraceRecord, column_name)
        success_case = case((TraceRecord.status == "success", 1), else_=0)
        failed_case = case((TraceRecord.status != "success", 1), else_=0)

        query = select(
            column,
            func.count(TraceRecord.trace_id),
            func.sum(success_case),
            func.sum(failed_case),
            func.coalesce(func.sum(TraceRecord.cost_usd), 0.0),
            func.coalesce(func.avg(TraceRecord.cost_usd), 0.0),
        ).group_by(column)

        for condition in filters:
            query = query.where(condition)

        rows = session.execute(
            query.order_by(func.coalesce(func.sum(TraceRecord.cost_usd), 0.0).desc())
        ).all()

        return [
            CostBreakdownItem(
                key=row[0] if row[0] is not None else "unknown",
                request_count=int(row[1] or 0),
                success_count=int(row[2] or 0),
                failed_count=int(row[3] or 0),
                total_cost_usd=round(float(row[4] or 0.0), 6),
                avg_cost_usd=round(float(row[5] or 0.0), 6),
            )
            for row in rows
        ]

    def _build_trace_filters(
        self,
        *,
        feature: str | None,
        model: str | None,
        tenant_id: str | None,
        prompt_template_name: str | None,
        prompt_template_version: str | None,
    ) -> list:
        filters = []
        if feature is not None:
            filters.append(TraceRecord.feature == feature)
        if model is not None:
            filters.append(TraceRecord.model == model)
        if tenant_id is not None:
            filters.append(TraceRecord.tenant_id == tenant_id)
        if prompt_template_name is not None:
            filters.append(TraceRecord.prompt_template_name == prompt_template_name)
        if prompt_template_version is not None:
            filters.append(TraceRecord.prompt_template_version == prompt_template_version)
        return filters

    def _build_trace_query(self, filters: list):
        query = select(TraceRecord)
        for condition in filters:
            query = query.where(condition)
        return query

    def _load_model_calls_by_trace(
        self,
        session,
        traces: list[TraceRecord],
    ) -> dict[str, list[ModelCallRecord]]:
        trace_ids = [trace.trace_id for trace in traces]
        if not trace_ids:
            return {}

        model_calls = session.scalars(
            select(ModelCallRecord)
            .where(ModelCallRecord.trace_id.in_(trace_ids))
            .order_by(ModelCallRecord.attempt.asc(), ModelCallRecord.created_at.asc())
        ).all()
        grouped: dict[str, list[ModelCallRecord]] = defaultdict(list)
        for call in model_calls:
            grouped[call.trace_id].append(call)
        return dict(grouped)

    def _build_reliability_accumulator(
        self,
        traces: list[TraceRecord],
        model_calls_by_trace: dict[str, list[ModelCallRecord]],
    ) -> ReliabilityAccumulator:
        accumulator = ReliabilityAccumulator()
        for trace in traces:
            accumulator.add(trace, model_calls_by_trace.get(trace.trace_id, []))
        return accumulator

    def _build_reliability_breakdown(
        self,
        traces: list[TraceRecord],
        model_calls_by_trace: dict[str, list[ModelCallRecord]],
        *,
        key_fn,
    ) -> list[ReliabilityBreakdownItem]:
        grouped: dict[str, ReliabilityAccumulator] = {}
        for trace in traces:
            key = key_fn(trace)
            accumulator = grouped.setdefault(key, ReliabilityAccumulator())
            accumulator.add(trace, model_calls_by_trace.get(trace.trace_id, []))

        return [
            self._to_reliability_breakdown_item(key, accumulator)
            for key, accumulator in sorted(
                grouped.items(),
                key=lambda item: (-item[1].request_count, item[0]),
            )
        ]

    def _to_reliability_breakdown_item(
        self,
        key: str,
        accumulator: ReliabilityAccumulator,
    ) -> ReliabilityBreakdownItem:
        return ReliabilityBreakdownItem(
            key=key,
            request_count=accumulator.request_count,
            success_count=accumulator.success_count,
            validation_failed_count=accumulator.validation_failed_count,
            provider_error_count=accumulator.provider_error_count,
            fallback_count=accumulator.fallback_count,
            repair_attempted_count=accumulator.repair_attempted_count,
            repair_recovered_count=accumulator.repair_recovered_count,
            success_rate=self._rate(accumulator.success_count, accumulator.request_count),
            validation_failure_rate=self._rate(
                accumulator.validation_failed_count,
                accumulator.request_count,
            ),
            provider_error_rate=self._rate(
                accumulator.provider_error_count,
                accumulator.request_count,
            ),
            fallback_rate=self._rate(
                accumulator.fallback_count,
                accumulator.request_count,
            ),
            repair_attempt_rate=self._rate(
                accumulator.repair_attempted_count,
                accumulator.request_count,
            ),
            repair_recovery_rate=self._rate(
                accumulator.repair_recovered_count,
                accumulator.repair_attempted_count,
            ),
            avg_attempt_count=self._average_attempt_count(accumulator),
        )

    def _prompt_template_key(self, trace_record: TraceRecord) -> str:
        name = trace_record.prompt_template_name
        version = trace_record.prompt_template_version
        if name and version:
            return f"{name}@{version}"
        if name:
            return name
        if version:
            return version
        return "unknown"

    def _rate(self, numerator: int, denominator: int) -> float:
        if denominator == 0:
            return 0.0
        return round(numerator / denominator, 4)

    def _average_attempt_count(self, accumulator: ReliabilityAccumulator) -> float:
        if accumulator.request_count == 0:
            return 0.0
        return round(accumulator.total_attempt_count / accumulator.request_count, 2)

    def _build_validation_summary(self, record) -> Any:
        if record.schema_valid is None and record.business_rules_valid is None:
            return None

        from app.schemas.llm import ValidationSummary

        return ValidationSummary(
            schema_valid=bool(record.schema_valid),
            business_rules_valid=record.business_rules_valid,
            errors=None,
        )

    def _build_usage_summary(self, record) -> Any:
        from app.schemas.llm import UsageSummary

        return UsageSummary(
            input_tokens=record.input_tokens,
            output_tokens=record.output_tokens,
            cached_input_tokens=record.cached_input_tokens,
            cost_usd=round(record.cost_usd, 6),
        )

    def _build_fallback_summary(self, record) -> Any:
        from app.schemas.llm import FallbackSummary

        return FallbackSummary(
            used=record.fallback_used,
            level=record.fallback_level,
        )

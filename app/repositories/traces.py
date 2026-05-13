import hashlib
import json
import logging
from typing import Any

from sqlalchemy.exc import SQLAlchemyError

from app.core.config import get_settings
from app.db.session import session_scope
from app.models.trace import ModelCallRecord, TraceRecord
from app.schemas.llm import GatewayExecuteRequest, GatewayExecuteResponse

logger = logging.getLogger(__name__)


class TraceRepository:
    def record_success(
        self,
        *,
        trace_id: str,
        payload: GatewayExecuteRequest,
        provider_name: str,
        response: GatewayExecuteResponse,
        latency_ms: int,
    ) -> None:
        settings = get_settings()
        if not settings.trace_persistence_enabled:
            return

        metadata, tenant_id, user_id_hash = self._sanitize_metadata(payload.metadata)
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
        call_record = ModelCallRecord(
            trace_id=trace_id,
            attempt=1,
            provider=provider_name,
            model=response.model,
            status=response.status,
            error_type=None,
            input_tokens=usage.input_tokens if usage else 0,
            output_tokens=usage.output_tokens if usage else 0,
            cached_input_tokens=usage.cached_input_tokens if usage else 0,
            latency_ms=latency_ms,
            cost_usd=usage.cost_usd if usage else 0.0,
        )
        self._persist(trace_record, call_record)

    def record_failure(
        self,
        *,
        trace_id: str,
        payload: GatewayExecuteRequest,
        provider_name: str,
        model_name: str | None,
        error_type: str,
        latency_ms: int,
    ) -> None:
        settings = get_settings()
        if not settings.trace_persistence_enabled:
            return

        metadata, tenant_id, user_id_hash = self._sanitize_metadata(payload.metadata)

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
            tenant_id=tenant_id,
            user_id_hash=user_id_hash,
            request_metadata=metadata,
            input_preview=self._maybe_input_preview(settings, payload.input),
            output_preview=None,
            input_tokens=0,
            output_tokens=0,
            cached_input_tokens=0,
            latency_ms=latency_ms,
            cost_usd=0.0,
            schema_valid=None,
            business_rules_valid=None,
            fallback_used=False,
            fallback_level=0,
        )
        call_record = ModelCallRecord(
            trace_id=trace_id,
            attempt=1,
            provider=provider_name,
            model=model_name or "unknown",
            status="provider_error",
            error_type=error_type,
            input_tokens=0,
            output_tokens=0,
            cached_input_tokens=0,
            latency_ms=latency_ms,
            cost_usd=0.0,
        )
        self._persist(trace_record, call_record)

    def _persist(self, trace_record: TraceRecord, call_record: ModelCallRecord) -> None:
        try:
            with session_scope() as session:
                session.add(trace_record)
                session.flush()
                session.add(call_record)
        except SQLAlchemyError:
            logger.exception("Trace persistence failed for trace_id=%s", trace_record.trace_id)

    def _sanitize_metadata(
        self,
        metadata: dict[str, Any],
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

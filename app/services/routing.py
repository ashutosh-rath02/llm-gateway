import json
from dataclasses import dataclass

from app.core.errors import GatewayError
from app.core.model_registry import ModelProfile, get_models_for_provider
from app.core.pricing import calculate_cost_usd
from app.schemas.llm import GatewayExecuteRequest


@dataclass(frozen=True, slots=True)
class RoutingDecision:
    provider_name: str
    initial_model: str
    fallback_models: list[str]
    estimated_input_tokens: int
    estimated_output_tokens: int
    reason: str


class RoutingService:
    def plan(self, payload: GatewayExecuteRequest, default_provider: str) -> RoutingDecision:
        provider_name = payload.provider or default_provider
        candidates = get_models_for_provider(provider_name)
        if not candidates:
            raise GatewayError(
                f"No models are registered for provider '{provider_name}'.",
                error_type="routing_provider_unavailable",
                status_code=400,
            )

        estimated_input_tokens, estimated_output_tokens = self._estimate_tokens(payload)
        eligible = self._eligible_models(
            payload,
            candidates,
            estimated_input_tokens=estimated_input_tokens,
            estimated_output_tokens=estimated_output_tokens,
        )
        if not eligible:
            raise GatewayError(
                "No eligible model satisfies the request constraints.",
                error_type="routing_no_eligible_model",
                status_code=400,
            )

        selected, reason = self._select_model(
            payload,
            eligible,
            estimated_input_tokens=estimated_input_tokens,
            estimated_output_tokens=estimated_output_tokens,
        )
        fallback_models = [
            model.name
            for model in sorted(eligible, key=lambda item: item.quality_rank)
            if model.quality_rank > selected.quality_rank
        ]

        return RoutingDecision(
            provider_name=provider_name,
            initial_model=selected.name,
            fallback_models=fallback_models,
            estimated_input_tokens=estimated_input_tokens,
            estimated_output_tokens=estimated_output_tokens,
            reason=reason,
        )

    def can_attempt_model(
        self,
        model_name: str,
        payload: GatewayExecuteRequest,
        *,
        estimated_input_tokens: int,
        estimated_output_tokens: int,
        cost_spent_usd: float,
        elapsed_latency_ms: int,
    ) -> bool:
        estimated_cost_usd = calculate_cost_usd(
            model_name,
            estimated_input_tokens,
            estimated_output_tokens,
        )
        if cost_spent_usd + estimated_cost_usd > payload.cost_budget_usd:
            return False

        profile = self._find_model_profile(payload.provider, model_name)
        if profile is None:
            return False

        return elapsed_latency_ms + profile.estimated_latency_ms <= payload.latency_budget_ms

    def build_gateway_metadata(
        self,
        payload: GatewayExecuteRequest,
        decision: RoutingDecision,
        *,
        attempts: int,
        final_status: str,
        final_error_type: str | None = None,
    ) -> dict:
        return {
            "routing": {
                "policy": payload.routing_policy,
                "provider": decision.provider_name,
                "initial_model": decision.initial_model,
                "fallback_models": decision.fallback_models,
                "reason": decision.reason,
                "estimated_input_tokens": decision.estimated_input_tokens,
                "estimated_output_tokens": decision.estimated_output_tokens,
            },
            "final": {
                "attempt_count": attempts,
                "fallback_used": attempts > 1,
                "final_status": final_status,
                "final_error_type": final_error_type,
            },
        }

    def _select_model(
        self,
        payload: GatewayExecuteRequest,
        eligible: list[ModelProfile],
        *,
        estimated_input_tokens: int,
        estimated_output_tokens: int,
    ) -> tuple[ModelProfile, str]:
        if payload.requested_model:
            explicit = next(
                (model for model in eligible if model.name == payload.requested_model),
                None,
            )
            if explicit is None:
                raise GatewayError(
                    (
                        f"Requested model '{payload.requested_model}' "
                        "is not eligible for this request."
                    ),
                    error_type="routing_requested_model_ineligible",
                    status_code=400,
                )
            return explicit, f"Requested model '{payload.requested_model}' was used explicitly."

        if payload.routing_policy == "explicit_model":
            raise GatewayError(
                "routing_policy='explicit_model' requires requested_model.",
                error_type="routing_missing_requested_model",
                status_code=400,
            )

        if payload.routing_policy == "cost_optimized":
            selected = min(
                eligible,
                key=lambda model: (
                    calculate_cost_usd(
                        model.name,
                        estimated_input_tokens,
                        estimated_output_tokens,
                    ),
                    model.quality_rank,
                    model.latency_rank,
                ),
            )
            return selected, "Selected the cheapest eligible model under the request constraints."

        if payload.routing_policy == "quality_optimized":
            selected = max(eligible, key=lambda model: (model.quality_rank, -model.latency_rank))
            return selected, "Selected the highest-quality eligible model."

        selected = self._select_balanced_model(payload, eligible)
        return selected, "Selected the best balanced model for task type, risk, schema, and budget."

    def _select_balanced_model(
        self,
        payload: GatewayExecuteRequest,
        eligible: list[ModelProfile],
    ) -> ModelProfile:
        if payload.risk_level == "high":
            return max(eligible, key=lambda model: (model.quality_rank, -model.latency_rank))

        if payload.schema_ is not None:
            structured = [model for model in eligible if model.quality_rank >= 3]
            if structured:
                return min(structured, key=lambda model: (model.quality_rank, model.latency_rank))

        if payload.task_type == "faq" and payload.risk_level == "low":
            lightweight = [model for model in eligible if model.quality_rank <= 2]
            if lightweight:
                return min(lightweight, key=lambda model: (model.quality_rank, model.latency_rank))

        target_quality = 3
        return min(
            eligible,
            key=lambda model: (abs(model.quality_rank - target_quality), model.latency_rank),
        )

    def _eligible_models(
        self,
        payload: GatewayExecuteRequest,
        candidates: list[ModelProfile],
        *,
        estimated_input_tokens: int,
        estimated_output_tokens: int,
    ) -> list[ModelProfile]:
        filtered: list[ModelProfile] = []
        for model in candidates:
            if payload.schema_ is not None and not model.supports_structured_output:
                continue
            if estimated_input_tokens > model.max_context_tokens:
                continue
            estimated_cost = calculate_cost_usd(
                model.name,
                estimated_input_tokens,
                estimated_output_tokens,
            )
            if estimated_cost > payload.cost_budget_usd:
                continue
            if model.estimated_latency_ms > payload.latency_budget_ms:
                continue
            filtered.append(model)
        return filtered

    def _estimate_tokens(self, payload: GatewayExecuteRequest) -> tuple[int, int]:
        context_words = sum(len(item.content.split()) for item in payload.context)
        schema_words = (
            len(json.dumps(payload.schema_).split())
            if payload.schema_ is not None
            else 0
        )
        input_tokens = max(1, len(payload.input.split()) + context_words + schema_words)
        output_tokens = 180 if payload.schema_ is not None else 80
        return input_tokens, output_tokens

    def _find_model_profile(
        self,
        provider_name: str | None,
        model_name: str,
    ) -> ModelProfile | None:
        if provider_name is None:
            for profiles in (
                get_models_for_provider("mock"),
                get_models_for_provider("openai_compatible"),
            ):
                for profile in profiles:
                    if profile.name == model_name:
                        return profile
            return None

        return next(
            (
                profile
                for profile in get_models_for_provider(provider_name)
                if profile.name == model_name
            ),
            None,
        )

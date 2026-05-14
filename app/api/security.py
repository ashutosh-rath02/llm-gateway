from dataclasses import dataclass

from fastapi import Header, HTTPException

from app.core.config import get_settings
from app.schemas.evals import EvalExportRequest
from app.schemas.llm import GatewayExecuteRequest
from app.schemas.trace import TraceDetailResponse


@dataclass(frozen=True, slots=True)
class AuthContext:
    name: str
    role: str
    tenant_id: str | None
    allowed_features: tuple[str, ...] = ()

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


def get_auth_context(
    authorization: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None),
) -> AuthContext:
    settings = get_settings()
    if not settings.auth_enabled:
        return AuthContext(name="local-dev", role="admin", tenant_id=None)

    token = _extract_token(authorization, x_api_key)
    if token is None:
        raise _auth_error(
            status_code=401,
            error_type="auth_required",
            message="Authentication is required for this endpoint.",
        )

    key_settings = settings.auth_api_keys.get(token)
    if key_settings is None:
        raise _auth_error(
            status_code=401,
            error_type="auth_invalid_api_key",
            message="The supplied API key is invalid.",
        )

    if key_settings.role == "tenant" and not key_settings.tenant_id:
        raise _auth_error(
            status_code=500,
            error_type="auth_config_invalid",
            message="Tenant-scoped API keys must define a tenant_id.",
        )

    return AuthContext(
        name=key_settings.name,
        role=key_settings.role,
        tenant_id=key_settings.tenant_id,
        allowed_features=tuple(key_settings.allowed_features),
    )


def scope_execute_payload(
    payload: GatewayExecuteRequest,
    auth: AuthContext,
) -> GatewayExecuteRequest:
    metadata = dict(payload.metadata)
    tenant_id = metadata.get("tenant_id")

    if auth.tenant_id is not None:
        if tenant_id is not None and tenant_id != auth.tenant_id:
            raise _auth_error(
                status_code=403,
                error_type="auth_tenant_mismatch",
                message="The request tenant_id does not match the authenticated tenant.",
            )
        metadata["tenant_id"] = auth.tenant_id

    if auth.allowed_features and payload.feature not in auth.allowed_features:
        raise _auth_error(
            status_code=403,
            error_type="auth_feature_forbidden",
            message="This API key is not allowed to call the requested feature.",
        )

    return payload.model_copy(update={"metadata": metadata})


def require_trace_access(trace: TraceDetailResponse, auth: AuthContext) -> None:
    if auth.is_admin:
        return
    if trace.tenant_id != auth.tenant_id:
        raise HTTPException(status_code=404, detail={"message": "Trace not found."})


def resolve_tenant_scope(requested_tenant_id: str | None, auth: AuthContext) -> str | None:
    if auth.is_admin:
        return requested_tenant_id
    if requested_tenant_id is not None and requested_tenant_id != auth.tenant_id:
        raise _auth_error(
            status_code=403,
            error_type="auth_tenant_mismatch",
            message="The requested tenant scope does not match the authenticated tenant.",
        )
    return auth.tenant_id


def scope_eval_export_request(
    payload: EvalExportRequest,
    auth: AuthContext,
) -> EvalExportRequest:
    scoped_tenant_id = resolve_tenant_scope(payload.tenant_id, auth)
    return payload.model_copy(update={"tenant_id": scoped_tenant_id})


def _extract_token(
    authorization: str | None,
    x_api_key: str | None,
) -> str | None:
    if x_api_key:
        return x_api_key.strip() or None
    if not authorization:
        return None

    scheme, _, credentials = authorization.partition(" ")
    if scheme.lower() != "bearer" or not credentials.strip():
        return None
    return credentials.strip()


def _auth_error(*, status_code: int, error_type: str, message: str) -> HTTPException:
    headers = {"WWW-Authenticate": "Bearer"} if status_code == 401 else None
    return HTTPException(
        status_code=status_code,
        detail={"error_type": error_type, "message": message},
        headers=headers,
    )

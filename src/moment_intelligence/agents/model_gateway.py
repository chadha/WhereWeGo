"""Provider-neutral model gateway (ADR-003).

The default is a local mock that makes no network calls. The Bedrock implementation is
present but disabled unless ``MODEL_GATEWAY=bedrock`` and ``BEDROCK_ENABLED=true`` are both
set, which requires explicit approval (ADR-010). Callers must always handle ``None`` and
fall back to deterministic output.
"""

from __future__ import annotations

from typing import Any, Protocol

from moment_intelligence.core.config import Settings


class GatewayDisabledError(RuntimeError):
    pass


class ModelGateway(Protocol):
    model_id: str

    async def generate_json(self, task: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        """Return structured output for ``task``, or ``None`` to request the fallback."""
        ...


class MockModelGateway:
    model_id = "local-mock"

    async def generate_json(self, task: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        return None


class BedrockModelGateway:
    """Skeleton. Wire boto3 ``bedrock-runtime`` here once Bedrock access is approved."""

    def __init__(self, settings: Settings, model_id: str = "configure-me") -> None:
        if not settings.bedrock_enabled:
            raise GatewayDisabledError("Bedrock is disabled (BEDROCK_ENABLED is not true)")
        self.model_id = model_id

    async def generate_json(self, task: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        raise GatewayDisabledError("Bedrock calls are not implemented in the local slice")


def build_gateway(settings: Settings) -> ModelGateway:
    if settings.model_gateway == "bedrock" and settings.bedrock_enabled:
        return BedrockModelGateway(settings)
    return MockModelGateway()

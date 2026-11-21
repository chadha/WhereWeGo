"""Runtime configuration read from environment variables.

Secrets are held as ``SecretStr`` so they never appear in reprs, logs or API responses.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal

from pydantic import SecretStr

ProviderMode = Literal["auto", "tavily", "mock"]
GatewayMode = Literal["mock", "bedrock"]

# Hard upper bound required by the product: never more than five search results.
MAX_SEARCH_RESULTS = 5


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    return float(raw) if raw else default


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    return int(raw) if raw else default


@dataclass(frozen=True)
class Settings:
    tavily_api_key: SecretStr | None
    provider_mode: ProviderMode
    tavily_base_url: str
    tavily_timeout_seconds: float
    tavily_max_retries: int
    tavily_max_results: int
    discovery_timeout_seconds: float
    model_gateway: GatewayMode
    bedrock_enabled: bool
    rate_limit_per_minute: int

    @property
    def use_tavily(self) -> bool:
        """Tavily is used only when credentials exist and mode allows it."""
        if self.provider_mode == "mock":
            return False
        return self.tavily_api_key is not None and bool(self.tavily_api_key.get_secret_value())


def load_settings() -> Settings:
    key = os.environ.get("TAVILY_API_KEY", "").strip()
    mode = os.environ.get("PROVIDER_MODE", "auto").strip().lower()
    if mode not in ("auto", "tavily", "mock"):
        mode = "auto"
    gateway = os.environ.get("MODEL_GATEWAY", "mock").strip().lower()
    if gateway not in ("mock", "bedrock"):
        gateway = "mock"
    return Settings(
        tavily_api_key=SecretStr(key) if key else None,
        provider_mode=mode,  # type: ignore[arg-type]
        tavily_base_url=os.environ.get("TAVILY_BASE_URL", "https://api.tavily.com"),
        tavily_timeout_seconds=_env_float("TAVILY_TIMEOUT_SECONDS", 8.0),
        tavily_max_retries=max(0, min(_env_int("TAVILY_MAX_RETRIES", 2), 3)),
        tavily_max_results=max(1, min(_env_int("TAVILY_MAX_RESULTS", 5), MAX_SEARCH_RESULTS)),
        discovery_timeout_seconds=_env_float("DISCOVERY_TIMEOUT_SECONDS", 20.0),
        model_gateway=gateway,  # type: ignore[arg-type]
        bedrock_enabled=os.environ.get("BEDROCK_ENABLED", "false").lower() == "true",
        rate_limit_per_minute=_env_int("DISCOVER_RATE_LIMIT_PER_MINUTE", 30),
    )

"""Common provider adapter interface (see docs/architecture.md, section 5B)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict

from moment_intelligence.domain.contracts import Offer, ProviderSearchQuery


class ProviderConfiguration(BaseModel):
    """What an adapter can do and whether it may be used. Declared, not assumed."""

    model_config = ConfigDict(extra="forbid")

    provider_id: str
    enabled: bool
    environment: Literal["local", "dev", "staging", "prod"] = "local"
    kind: Literal["web_search", "provider_catalogue", "demo"]
    requires_credentials: bool
    supports_search: bool
    supports_price: bool
    supports_availability: bool
    supports_affiliate_tracking: bool
    last_successful_sync: datetime | None = None
    terms_reviewed_at: datetime | None = None


class ProviderResult(BaseModel):
    """What a provider returned, plus operational metadata for observability."""

    model_config = ConfigDict(extra="forbid")

    offers: list[Offer]
    provider_id: str
    attempts: int = 1
    retries: int = 0
    latency_ms: int = 0
    raw_result_count: int = 0
    duplicates_removed: int = 0


class ExperienceProvider(Protocol):
    configuration: ProviderConfiguration

    async def search(self, query: ProviderSearchQuery) -> ProviderResult: ...

"""Generate JSON Schemas and the OpenAPI document from the Pydantic contracts.

Usage: python scripts/export_schemas.py
"""

from __future__ import annotations

import json
import os
from pathlib import Path

os.environ.setdefault("PROVIDER_MODE", "mock")  # never needs credentials

from app.main import create_app  # noqa: E402
from moment_intelligence.domain import contracts  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "contracts" / "schemas"
MODELS = [
    contracts.DiscoveryRequest,
    contracts.ProviderSearchQuery,
    contracts.Offer,
    contracts.RankingExplanation,
    contracts.MomentCollectionResponse,
    contracts.BehavioralEvent,
    contracts.ClientEventRequest,
]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for model in MODELS:
        path = OUT / f"{model.__name__}.schema.json"
        path.write_text(json.dumps(model.model_json_schema(), indent=2) + "\n")
    (OUT / "openapi.json").write_text(json.dumps(create_app().openapi(), indent=2) + "\n")
    print(f"wrote {len(MODELS) + 1} files to {OUT}")


if __name__ == "__main__":
    main()

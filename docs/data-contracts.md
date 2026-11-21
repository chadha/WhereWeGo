# Data contracts

Pydantic models are the **single source of truth**. OpenAPI and JSON Schema are generated from them so the frontend, the backend and Databricks never disagree about what the data means. Every contract carries a `schema_version`; incompatible versions are rejected.

Full examples live in [`contracts/examples/`](../contracts/examples).

Contracts to implement: `DiscoveryRequest`, `IntentResult`, `ProviderSearchQuery`, `Offer`, `MomentCollection`, `BehavioralEvent`, `AgentExecutionTrace`, `ProviderConfiguration`, `RankingExplanation`.

## 1. DiscoveryRequest
Sent by the website to `POST /v1/discover`. Example: [discovery_request.json](../contracts/examples/discovery_request.json).

- Dates, budget and locale are validated.
- `session_id` is random and short-lived.
- No email, no name, no unnecessary personal data.

## 2. IntentResult
Output of the Intent Agent. Example: [intent_result.json](../contracts/examples/intent_result.json).

- `confidence` is not a guarantee that the LLM understood correctly; it is tested against labeled evaluation data.
- If there is important ambiguity, ask the user one question only.

## 3. Offer
One unified contract regardless of provider. Example: [offer.json](../contracts/examples/offer.json).

**Non-negotiable rules**
- Never invent a price or availability.
- `per_person` is never treated as `total`.
- An `affiliate_url` is not activated before approval.
- `last_verified_at` must be a real timestamp.
- The demo catalogue is never mixed with live provider inventory (`data_source`, `is_illustrative`).

## 4. BehavioralEvent
Every interaction becomes one unified event. Example: [behavioral_event.json](../contracts/examples/behavioral_event.json).

This lets us analyse acquisition, conversion and demand without collecting personal data we do not need. Events are versioned, validated and idempotent (`event_id`).

Event types: `discovery_started`, `preferences_submitted`, `discovery_completed`, `collection_viewed`, `offer_viewed`, `offer_clicked`, `no_results_found`, `affiliate_conversion_confirmed`.

Never infer a confirmed booking from an outbound click. `affiliate_conversion_confirmed` is only emitted from a trusted provider or affiliate-network confirmation.

## 5. MomentCollectionResponse
Returned by the API. Example: [moment_collection_response.json](../contracts/examples/moment_collection_response.json).

`price_status` and `availability_status` always state honestly whether values are illustrative, estimated or verified.

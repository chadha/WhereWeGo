# ADR-008: Consent-aware anonymous behavioral analytics

**Status:** Accepted
**Date:** 2026-11-21

## Context
We operate in Germany (GDPR). Analytics and advertising tracking require consent and legal review.

## Decision
Random, short-lived session IDs; no names or emails for discovery; consent state stored with events; retention policy for raw events; deletion workflow where required; no sensitive data in prompts or traces. The consent UI is real, not a cosmetic checkbox.

## Consequences
Lower legal risk and user trust. Some attribution is lost when users decline, which we accept.

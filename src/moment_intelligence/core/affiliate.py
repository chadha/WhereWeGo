"""Deterministic affiliate link building (ADR-013).

An outbound link is tagged only when its host belongs to a partner that a human has
configured in ``AFFILIATE_RULES``. Without rules nothing is tagged, so the default
behaviour is exactly the pre-affiliate behaviour. Nothing here invents a link: the
destination is always the stored source URL, with the partner's own tracking parameters
added. The parameter names and values come from the partner dashboard, never from code
or from a model.

``AFFILIATE_RULES`` is a JSON list, for example::

    [{"domain": "partner.example", "params": {"partner_id": "ABC123"},
      "click_id_param": "cmp"}]
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

_DOMAIN = re.compile(r"^(?=.{4,253}$)([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,24}$")
_PARAM_NAME = re.compile(r"^[A-Za-z0-9_\-]{1,40}$")
_PARAM_VALUE = re.compile(r"^[A-Za-z0-9_\-\.]{1,200}$")
MAX_RULES = 20


class AffiliateConfigError(ValueError):
    """Raised at startup for a malformed AFFILIATE_RULES value. Never echoes the value."""


@dataclass(frozen=True)
class AffiliateRule:
    """One approved partner: which host we may tag and with which parameters."""

    domain: str
    params: tuple[tuple[str, str], ...]
    click_id_param: str | None = None

    def matches(self, host: str) -> bool:
        return host == self.domain or host.endswith("." + self.domain)


def parse_affiliate_rules(raw: str | None) -> tuple[AffiliateRule, ...]:
    """Parse and validate ``AFFILIATE_RULES``. Empty or missing means no affiliate links."""
    if raw is None or not raw.strip():
        return ()
    try:
        data = json.loads(raw)
    except ValueError as exc:
        raise AffiliateConfigError("AFFILIATE_RULES is not valid JSON") from exc
    if not isinstance(data, list) or len(data) > MAX_RULES:
        raise AffiliateConfigError(f"AFFILIATE_RULES must be a list of at most {MAX_RULES} rules")
    rules: list[AffiliateRule] = []
    seen: set[str] = set()
    for index, item in enumerate(data):
        where = f"AFFILIATE_RULES[{index}]"
        if not isinstance(item, dict) or set(item) - {"domain", "params", "click_id_param"}:
            raise AffiliateConfigError(f"{where} must have only domain, params, click_id_param")
        domain = item.get("domain")
        if not isinstance(domain, str) or not _DOMAIN.match(domain.strip().lower()):
            raise AffiliateConfigError(f"{where}.domain must be a plain host name")
        domain = domain.strip().lower().removeprefix("www.")
        if domain in seen:
            raise AffiliateConfigError(f"{where}.domain is listed twice")
        seen.add(domain)
        params = item.get("params")
        if not isinstance(params, dict) or not params:
            raise AffiliateConfigError(f"{where}.params must be a non-empty object")
        pairs: list[tuple[str, str]] = []
        for name, value in params.items():
            if not isinstance(name, str) or not _PARAM_NAME.match(name):
                raise AffiliateConfigError(f"{where}.params has an invalid parameter name")
            if not isinstance(value, str) or not _PARAM_VALUE.match(value):
                raise AffiliateConfigError(f"{where}.params has an invalid parameter value")
            pairs.append((name, value))
        click_param = item.get("click_id_param")
        if click_param is not None and (
            not isinstance(click_param, str)
            or not _PARAM_NAME.match(click_param)
            or click_param in params
        ):
            raise AffiliateConfigError(f"{where}.click_id_param is invalid")
        rules.append(AffiliateRule(domain, tuple(sorted(pairs)), click_param))
    return tuple(rules)


def build_affiliate_url(
    source_url: str | None, rules: tuple[AffiliateRule, ...], click_id: str | None = None
) -> str | None:
    """Return the source URL tagged for its partner, or ``None`` when no rule applies.

    Only https URLs on a configured partner host are tagged. Parameters with the same
    names already present in the URL are replaced, so a link found on the web can never
    carry somebody else's partner ID through our redirect.
    """
    if not source_url or not rules:
        return None
    try:
        parts = urlsplit(source_url)
    except ValueError:
        return None
    if parts.scheme != "https" or not parts.hostname or parts.username or parts.password:
        return None
    host = parts.hostname.lower()
    rule = next((r for r in rules if r.matches(host)), None)
    if rule is None:
        return None
    ours = list(rule.params)
    if rule.click_id_param and click_id and _PARAM_VALUE.match(click_id):
        ours.append((rule.click_id_param, click_id))
    reserved = {name for name, _ in ours}
    if rule.click_id_param:
        reserved.add(rule.click_id_param)
    kept = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if k not in reserved]
    return urlunsplit(
        (parts.scheme, parts.netloc, parts.path, urlencode(kept + ours), parts.fragment)
    )

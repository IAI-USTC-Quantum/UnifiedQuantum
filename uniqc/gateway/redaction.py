"""Redaction helpers for gateway API responses.

Task ``metadata`` / ``result`` payloads are free-form: callers may pass
backend credentials, proxy configuration or other sensitive values at
submission time, and they end up persisted on the task record. The
gateway must never echo those back over the REST API, so API responses
pass through :func:`redact_sensitive` before serialization. Only the
response is scrubbed — the stored task record keeps the original data.
"""

from __future__ import annotations

from typing import Any

REDACTED = "[REDACTED]"

# Keys whose values are scrubbed from API responses. Matching is
# case-insensitive and requires the token to appear as a full
# alphanumeric word, so ``api_key`` / ``QUARK_API_KEY`` match while
# ``monkey`` or ``keyboard`` do not.
_SENSITIVE_WORDS = ("token", "key", "secret", "password", "passwd", "credential", "proxy", "auth")


def _is_sensitive_key(key: object) -> bool:
    if not isinstance(key, str):
        return False
    lowered = key.lower()
    return any(
        lowered == word
        or lowered.startswith(word + "_")
        or lowered.startswith(word + "-")
        or lowered.endswith("_" + word)
        or lowered.endswith("-" + word)
        or f"_{word}_" in lowered
        or f"-{word}-" in lowered
        for word in _SENSITIVE_WORDS
    )


def redact_sensitive(value: Any) -> Any:
    """Return a copy of *value* with sensitive dict entries redacted.

    Recurses into nested dicts and lists; any dict entry whose key names
    a credential (token, api key, password, proxy, ...) is replaced with
    ``REDACTED``. Falsy values are left untouched so redaction never
    fabricates non-empty data.
    """
    if isinstance(value, dict):
        return {
            key: REDACTED if _is_sensitive_key(key) and nested else redact_sensitive(nested)
            for key, nested in value.items()
        }
    if isinstance(value, list):
        return [redact_sensitive(item) for item in value]
    return value

"""Shopify webhook HMAC verification (spec 3.5).

Must be computed over the RAW request body bytes, read before any JSON
parsing, using the webhook/app shared secret, base64-encoded, compared with
a constant-time comparison.
"""
from __future__ import annotations

import base64
import hashlib
import hmac


def verify_shopify_hmac(raw_body: bytes, header_value: str | None, secret: str) -> bool:
    if not header_value:
        return False
    digest = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).digest()
    computed = base64.b64encode(digest).decode("utf-8")
    return hmac.compare_digest(computed, header_value)

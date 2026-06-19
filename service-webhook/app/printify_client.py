"""Printify Orders/Uploads client (spec 3.1, 3.1a, 3.2, 3.3).

No hard-coded per-minute rate limits — the spec found only the documented
200/30min publishing limit (which doesn't apply to order-driven product
creation) and explicitly says NOT to hard-code the unconfirmed 600/min and
100/min figures from the v1 draft. Instead: exponential backoff with
jitter on every 429, logged.
"""
from __future__ import annotations

import base64
import logging
import random
import time

import httpx

from app.config import PRINTIFY_API_BASE, PRINTIFY_API_TOKEN, PRINTIFY_SHOP_ID

logger = logging.getLogger("service-webhook.printify")

_MAX_RETRIES = 5
_BASE_BACKOFF_S = 1.0


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {PRINTIFY_API_TOKEN}"}


def _request_with_backoff(method: str, url: str, **kwargs) -> httpx.Response:
    for attempt in range(_MAX_RETRIES):
        resp = httpx.request(method, url, headers=_headers(), timeout=30.0, **kwargs)
        if resp.status_code != 429:
            resp.raise_for_status()
            return resp
        delay = _BASE_BACKOFF_S * (2 ** attempt) + random.uniform(0, 1)
        logger.warning("Printify 429, backing off %.1fs (attempt %d/%d)", delay, attempt + 1, _MAX_RETRIES)
        time.sleep(delay)
    raise RuntimeError(f"Printify rate-limited after {_MAX_RETRIES} retries: {url}")


def upload_image(png_bytes: bytes, file_name: str) -> str:
    """Upload rendered PNG to Printify (spec 3.1a) rather than referencing an
    external URL directly. Returns the Printify upload id, stored as render_id
    per spec Section 0.

    UPDATE ME: confirm against the live Printify dev docs whether
    /v1/uploads/images.json wants base64 `contents` (used here) or a `url`
    field, and whether orders.json also accepts direct external src URLs as
    an alternative — the spec flags this as unconfirmed (3.1a, 3.7).
    """
    url = f"{PRINTIFY_API_BASE}/uploads/images.json"
    body = {
        "file_name": file_name,
        "contents": base64.b64encode(png_bytes).decode("ascii"),
    }
    resp = _request_with_backoff("POST", url, json=body)
    data = resp.json()
    return data["id"]


def create_order(*, external_id: str, line_items: list[dict], address_to: dict, shipping_method: int = 1) -> dict:
    """Create a Printify order (spec 3.1). Caller is responsible for the
    manual-hold gate (spec Section 0 item 3) — this function always submits."""
    url = f"{PRINTIFY_API_BASE}/shops/{PRINTIFY_SHOP_ID}/orders.json"
    body = {
        "external_id": external_id,
        "line_items": line_items,
        "shipping_method": shipping_method,
        "address_to": address_to,
        "send_shipping_notification": False,
    }
    resp = _request_with_backoff("POST", url, json=body)
    return resp.json()


def build_print_area_line_item(
    *,
    print_provider_id: int,
    blueprint_id: int,
    variant_id: int,
    quantity: int,
    upload_id: str,
    position: str = "front",
    x: float = 0.5,
    y: float = 0.5,
    scale: float = 1.0,
    angle: float = 0,
) -> dict:
    """Build a line_items[] entry per spec 3.1/3.2. `position` must match the
    blueprint's placeholder position (fetch via GET /products/{id}.json)."""
    return {
        "print_provider_id": print_provider_id,
        "blueprint_id": blueprint_id,
        "variant_id": variant_id,
        "quantity": quantity,
        "print_areas": {
            position: [{"src": upload_id, "x": x, "y": y, "scale": scale, "angle": angle}]
        },
    }

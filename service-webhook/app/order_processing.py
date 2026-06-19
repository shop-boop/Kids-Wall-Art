"""Core order-processing logic, invoked from the async /process-order route
(never inline in the webhook handler — see app/main.py for why).
"""
from __future__ import annotations

import logging

from script_payload import ScriptPayload
from app.config import MANUAL_HOLD_ENABLED
from app.printify_client import build_print_area_line_item, create_order, upload_image
from app.storage import get_storage

logger = logging.getLogger("service-webhook.order_processing")


class ManualHoldRequired(Exception):
    """Raised instead of submitting to Printify when MANUAL_HOLD_ENABLED is
    true (spec Section 0 item 3). Caller should persist the order for a
    native-reader review queue rather than treat this as a failure."""


def process_line_item(
    *,
    shopify_order_id: str,
    line_item_properties: dict,
    printify_print_provider_id: int,
    printify_blueprint_id: int,
    printify_variant_id: int,
    quantity: int,
    address_to: dict,
) -> dict:
    """Reads the customer-approved render reference and submits to Printify.

    Never re-transliterates from raw English (spec Section 0) — the
    _script_payload.render_id/render_hash is the only source of truth for
    what gets printed.
    """
    raw_payload = line_item_properties.get("_script_payload")
    if not raw_payload:
        raise ValueError(f"order {shopify_order_id}: line item missing _script_payload")

    payload = ScriptPayload.from_json(raw_payload)

    storage = get_storage()
    png_bytes = storage.get(payload.render_id)

    # UPDATE ME: verify the fetched bytes match what the customer approved.
    import hashlib

    actual_hash = hashlib.sha256(png_bytes).hexdigest()
    if actual_hash != payload.render_hash:
        raise ValueError(
            f"order {shopify_order_id}: render_hash mismatch for render_id "
            f"{payload.render_id} — refusing to submit a render that doesn't "
            f"match what the customer approved"
        )

    if MANUAL_HOLD_ENABLED:
        logger.info(
            "order %s held for manual review (render_id=%s, script=%s)",
            shopify_order_id, payload.render_id, payload.script,
        )
        raise ManualHoldRequired(shopify_order_id)

    upload_id = upload_image(png_bytes, file_name=f"{payload.render_id}.png")

    line_item = build_print_area_line_item(
        print_provider_id=printify_print_provider_id,
        blueprint_id=printify_blueprint_id,
        variant_id=printify_variant_id,
        quantity=quantity,
        upload_id=upload_id,
    )

    order = create_order(
        external_id=shopify_order_id,
        line_items=[line_item],
        address_to=address_to,
    )
    logger.info("order %s submitted to Printify: %s", shopify_order_id, order.get("id"))
    return order

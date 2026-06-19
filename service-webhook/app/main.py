"""service-webhook: Component D.

Two routes, intentionally separated so Shopify's webhook ack is never
blocked by a Printify call (spec Section 0 design decision):

  POST /webhooks/orders-create  -> verify HMAC, enqueue async work, ack <1s
  POST /internal/process-order  -> does the actual storage fetch + Printify
                                    call. Invoked by Cloud Tasks, not public.

UPDATE ME: /internal/process-order should be locked down (Cloud Run
ingress=internal, or an OIDC token check) once deployed — it is NOT
authenticated in this scaffold.
"""
from __future__ import annotations

import logging

from fastapi import FastAPI, Header, HTTPException, Request

from app.config import SHOPIFY_WEBHOOK_SECRET
from app.hmac_verify import verify_shopify_hmac
from app.order_processing import ManualHoldRequired, process_line_item
from app.tasks import enqueue_process_order

logger = logging.getLogger("service-webhook")

app = FastAPI(title="little-roots-service-webhook")


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}


@app.post("/webhooks/orders-create")
async def orders_create(request: Request, x_shopify_hmac_sha256: str | None = Header(default=None)):
    raw_body = await request.body()  # MUST read raw bytes before any JSON parsing (spec 3.5)

    if not verify_shopify_hmac(raw_body, x_shopify_hmac_sha256, SHOPIFY_WEBHOOK_SECRET):
        raise HTTPException(status_code=401, detail="invalid HMAC")

    order = await request.json()
    order_id = str(order.get("id"))

    # Enqueue async per-line-item processing; ack immediately so Shopify's
    # webhook retry logic never sees a timeout-induced duplicate delivery.
    for line_item in order.get("line_items", []):
        if "_script_payload" not in line_item.get("properties", {}):
            continue  # not a personalized item
        enqueue_process_order(order_id=order_id, line_item=line_item, shipping_address=order.get("shipping_address", {}))

    return {"received": True}


@app.post("/internal/process-order")
async def internal_process_order(request: Request):
    """Invoked by Cloud Tasks (or directly, in dev) with the payload built by
    app/tasks.py. UPDATE ME: restrict ingress before deploying — see module docstring."""
    body = await request.json()

    try:
        process_line_item(
            shopify_order_id=body["order_id"],
            line_item_properties=body["line_item"]["properties"],
            printify_print_provider_id=body["printify_print_provider_id"],
            printify_blueprint_id=body["printify_blueprint_id"],
            printify_variant_id=body["printify_variant_id"],
            quantity=body["line_item"].get("quantity", 1),
            address_to=body["address_to"],
        )
    except ManualHoldRequired:
        return {"status": "held_for_manual_review"}
    except Exception:
        logger.exception("failed to process order %s", body.get("order_id"))
        raise HTTPException(status_code=500, detail="processing failed")

    return {"status": "submitted"}

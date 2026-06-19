"""Cloud Tasks dispatch so /webhooks/orders-create can ack Shopify fast
without waiting on the Printify round-trip (spec Section 0 design decision).

UPDATE ME: this enqueues against a real Cloud Tasks queue once
GCP_PROJECT_ID / CLOUD_TASKS_QUEUE / PROCESS_ORDER_URL are filled in. Until
then it logs a warning and falls back to in-process (synchronous) calls so
local dev still works end-to-end.
"""
from __future__ import annotations

import json
import logging

from app.config import (
    CLOUD_TASKS_QUEUE,
    GCP_LOCATION,
    GCP_PROJECT_ID,
    PROCESS_ORDER_URL,
)
from app.variant_mapping import lookup

logger = logging.getLogger("service-webhook.tasks")


def _build_task_body(order_id: str, line_item: dict, shipping_address: dict) -> dict:
    printify_ids = lookup(str(line_item["variant_id"]))
    return {
        "order_id": order_id,
        "line_item": line_item,
        "printify_print_provider_id": printify_ids["print_provider_id"],
        "printify_blueprint_id": printify_ids["blueprint_id"],
        "printify_variant_id": printify_ids["variant_id"],
        "address_to": shipping_address,
    }


def enqueue_process_order(*, order_id: str, line_item: dict, shipping_address: dict) -> None:
    body = _build_task_body(order_id, line_item, shipping_address)

    placeholders_unset = "UPDATE_ME" in (GCP_PROJECT_ID, CLOUD_TASKS_QUEUE, PROCESS_ORDER_URL)
    if placeholders_unset:
        logger.warning(
            "Cloud Tasks not configured (GCP_PROJECT_ID/CLOUD_TASKS_QUEUE/"
            "PROCESS_ORDER_URL unset) — processing order %s inline. "
            "UPDATE ME before deploying: this defeats the fast-ack design.",
            order_id,
        )
        import httpx

        httpx.post(PROCESS_ORDER_URL or "http://localhost:8080/internal/process-order", json=body, timeout=60.0)
        return

    from google.cloud import tasks_v2  # type: ignore

    client = tasks_v2.CloudTasksClient()
    parent = client.queue_path(GCP_PROJECT_ID, GCP_LOCATION, CLOUD_TASKS_QUEUE)
    task = {
        "http_request": {
            "http_method": tasks_v2.HttpMethod.POST,
            "url": PROCESS_ORDER_URL,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(body).encode(),
        }
    }
    client.create_task(parent=parent, task=task)

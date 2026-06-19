"""Runtime config for service-webhook. UPDATE ME placeholders also tracked
in the top-level README checklist.
"""
from __future__ import annotations

import os


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


# --- Shopify ---
SHOPIFY_WEBHOOK_SECRET = _env("SHOPIFY_WEBHOOK_SECRET", "UPDATE_ME_shopify_webhook_secret")
SHOPIFY_API_VERSION = _env("SHOPIFY_API_VERSION", "2026-04")  # spec 3.6 — pin explicit stable version

# --- Printify ---
PRINTIFY_API_TOKEN = _env("PRINTIFY_API_TOKEN", "UPDATE_ME_printify_api_token")
PRINTIFY_SHOP_ID = _env("PRINTIFY_SHOP_ID", "UPDATE_ME_printify_shop_id")
PRINTIFY_API_BASE = "https://api.printify.com/v1"

# --- Storage (same bucket service-render wrote renders into) ---
STORAGE_BACKEND = _env("STORAGE_BACKEND", "gcs")
GCS_BUCKET = _env("GCS_BUCKET", "UPDATE_ME_gcs_bucket_name")
R2_BUCKET = _env("R2_BUCKET", "UPDATE_ME_r2_bucket_name")
R2_ACCOUNT_ID = _env("R2_ACCOUNT_ID", "UPDATE_ME_r2_account_id")
R2_ACCESS_KEY_ID = _env("R2_ACCESS_KEY_ID", "UPDATE_ME_r2_access_key_id")
R2_SECRET_ACCESS_KEY = _env("R2_SECRET_ACCESS_KEY", "UPDATE_ME_r2_secret_access_key")

# --- Launch-period manual hold (spec Section 0, item 3) ---
# When true, orders are recorded but NOT submitted to Printify; a native
# reader must approve via a separate release step. Relax to false once
# per-language confidence is established.
MANUAL_HOLD_ENABLED = _env("MANUAL_HOLD_ENABLED", "true").lower() == "true"

# --- Async dispatch so the Printify call never blocks the webhook ack ---
# UPDATE ME: wire a real Cloud Tasks queue name/project once GCP project is set.
GCP_PROJECT_ID = _env("GCP_PROJECT_ID", "UPDATE_ME_gcp_project_id")
GCP_LOCATION = _env("GCP_LOCATION", "us-central1")
CLOUD_TASKS_QUEUE = _env("CLOUD_TASKS_QUEUE", "UPDATE_ME_cloud_tasks_queue_name")
PROCESS_ORDER_URL = _env("PROCESS_ORDER_URL", "UPDATE_ME_service_webhook_internal_process_url")

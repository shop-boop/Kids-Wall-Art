"""Runtime config, loaded from env vars. All placeholders are flagged
"UPDATE ME" and also listed in the top-level README checklist.
"""
from __future__ import annotations

import os


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


# --- Transliteration backend selection (spec 1.4) ---
# "indicxlit" (default/primary), "input_tools" (optional secondary), "cloud_translation" (fallback)
TRANSLITERATE_BACKEND = _env("TRANSLITERATE_BACKEND", "indicxlit")

# --- Cloud Translation v3 (only used if TRANSLITERATE_BACKEND=cloud_translation) ---
GCP_PROJECT_ID = _env("GCP_PROJECT_ID", "UPDATE_ME_gcp_project_id")
GCP_LOCATION = _env("GCP_LOCATION", "global")

# --- Storage for rendered images (spec Section 0 design decision) ---
# "gcs" or "r2"
STORAGE_BACKEND = _env("STORAGE_BACKEND", "gcs")
GCS_BUCKET = _env("GCS_BUCKET", "UPDATE_ME_gcs_bucket_name")
R2_BUCKET = _env("R2_BUCKET", "UPDATE_ME_r2_bucket_name")
R2_ACCOUNT_ID = _env("R2_ACCOUNT_ID", "UPDATE_ME_r2_account_id")
R2_ACCESS_KEY_ID = _env("R2_ACCESS_KEY_ID", "UPDATE_ME_r2_access_key_id")
R2_SECRET_ACCESS_KEY = _env("R2_SECRET_ACCESS_KEY", "UPDATE_ME_r2_secret_access_key")

# --- Rendering ---
FONT_DIR = _env("FONT_DIR", os.path.join(os.path.dirname(__file__), "..", "fonts"))

# Maps script code -> font filename inside FONT_DIR. UPDATE ME once real
# Noto font files are bundled (see fonts/README.md).
SCRIPT_FONT_MAP = {
    "ta": "NotoSansTamil-Regular.ttf",
    "te": "NotoSansTelugu-Regular.ttf",
    "hi": "NotoSansDevanagari-Regular.ttf",
    "gu": "NotoSansGujarati-Regular.ttf",
    "kn": "NotoSansKannada-Regular.ttf",
    "ml": "NotoSansMalayalam-Regular.ttf",
    "mr": "NotoSansDevanagari-Regular.ttf",
    "pa": "NotoSansGurmukhi-Regular.ttf",
    "bn": "NotoSansBengali-Regular.ttf",
    "ur": "NotoNastaliqUrdu-Regular.ttf",
}

CORS_ALLOWED_ORIGIN = _env("CORS_ALLOWED_ORIGIN", "UPDATE_ME_storefront_origin")

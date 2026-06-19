# Little Roots by Moodscape — Personalization Stack

Implementation of [docs/spec-v2.md](docs/spec-v2.md). Scaffolded with
placeholder credentials/IDs throughout — **see the checklist below before
deploying anything.**

## Repo layout

```
little-roots/
  worker/            Cloudflare Worker (TS) — CORS/cache proxy in front of service-render
  theme-extension/   Shopify Theme App Extension (Liquid/JS) — Component B
  service-render/    Cloud Run, Python — Components A (transliteration) + C (rendering)
  service-webhook/   Cloud Run, Python — Component D (order webhook handler)
  shared/            _script_payload schema + transliterate() interface, imported by both Python services
  docs/              the v2 spec
```

`service-render` and `service-webhook` are separate Cloud Run services on
purpose: D must ack Shopify's webhook fast, C's container is heavy
(Pillow/RAQM/IndicXlit weights/fonts). See spec-v2.md "Repo layout decision"
for the full reasoning.

## Status

All four components are scaffolded and pass their local unit tests
(`shared/`'s payload contract, `service-render`'s rendering/backend syntax,
`service-webhook`'s HMAC verification and manual-hold/hash-mismatch gates).
Nothing has been deployed or run against live Shopify/Printify/GCP yet —
everything below is a placeholder until you fill it in.

## UPDATE ME — credentials, IDs, and config to fill in before deploying

Grep for `UPDATE_ME` / `UPDATE ME` across the repo to find every instance
(53 as of this scaffold). Grouped by what you'll need to obtain:

### Shopify
- `service-webhook/app/config.py` → `SHOPIFY_WEBHOOK_SECRET` (from the webhook subscription / app config)
- `worker/wrangler.toml` → `ALLOWED_ORIGIN` (your storefront's `https://your-store.myshopify.com` or custom domain)
- `theme-extension/blocks/little-roots-personalization.liquid` → set the `render_endpoint` block setting in the theme editor once the worker is deployed
- `theme-extension/README.md` → manual patch to `sections/main-product.liquid` (or your PDP section) to allow `@app` blocks — apply by hand in the Shopify code editor, no zip upload
- `service-webhook/app/variant_mapping.py` → populate `SHOPIFY_VARIANT_TO_PRINTIFY` once your Printify catalog exists (no documented API maps this automatically — see spec 3.2)

### Printify
- `service-webhook/app/config.py` → `PRINTIFY_API_TOKEN`, `PRINTIFY_SHOP_ID`
- `service-webhook/app/printify_client.py` → confirm `/v1/uploads/images.json` request shape (base64 `contents` vs. `url`) against the live dev docs (spec 3.1a, 3.7 — unconfirmed)
- `service-webhook/app/variant_mapping.py` → `print_provider_id` / `blueprint_id` / `variant_id` per Shopify variant (fetch via `GET /v1/shops/{shop_id}/products/{product_id}.json`)

### GCP / storage
- `service-render/app/config.py` and `service-webhook/app/config.py` → `GCS_BUCKET` (or `R2_*` if using Cloudflare R2 instead), `GCP_PROJECT_ID`
- `service-webhook/app/config.py` → `CLOUD_TASKS_QUEUE`, `PROCESS_ORDER_URL` (the deployed `service-webhook` URL's `/internal/process-order` route) — until set, `app/tasks.py` falls back to a synchronous HTTP call for local dev, which defeats the fast-ack design and must not ship to production
- `service-render/app/config.py` → `CORS_ALLOWED_ORIGIN`

### Cloudflare Worker
- `worker/wrangler.toml` → `SERVICE_RENDER_ORIGIN` (deployed `service-render` Cloud Run URL)

### Fonts (no credential, but required content)
- `service-render/fonts/README.md` → download and place the real Noto Indic `.ttf` files; without them `/render` raises `FileNotFoundError` by design (see comment in `service-render/app/rendering.py`)

### Security follow-ups before production
- `service-webhook/app/main.py` → `/internal/process-order` is currently unauthenticated; restrict Cloud Run ingress to internal-only or add an OIDC token check before deploying
- `service-render/Dockerfile` → verify the `libraqm` build-from-source step is still needed for the base image you actually use, or drop it if the Pillow wheel already bundles RAQM

## Cross-cutting reminders baked into the code (don't relax without re-reading spec Section 0)

- `service-webhook/app/order_processing.py` refuses to submit to Printify if the fetched render's SHA-256 doesn't match `_script_payload.render_hash` — this is the mechanism that guarantees the printed artifact is exactly what the customer approved.
- `MANUAL_HOLD_ENABLED` (`service-webhook/app/config.py`) defaults to `true` — orders are held for native-reader review, not auto-submitted, until you deliberately flip this per the spec's launch-period requirement.
- `service-webhook` never re-transliterates or re-renders; it only fetches the stored render by `render_id`.

## Local dev

```bash
# shared/ contract tests
pip install -e shared pytest
PYTHONPATH=service-render python -m pytest service-render/tests/
PYTHONPATH=service-webhook python -m pytest service-webhook/tests/

# worker
cd worker && npm install && npm run dev   # requires wrangler + a Cloudflare account login
```

`service-render` and `service-webhook` each need their heavier deps
(`requirements.txt`) and, for `service-render`, the Docker build (system
packages for RAQM, bundled fonts, IndicXlit weight prefetch) to run for
real — see each Dockerfile.

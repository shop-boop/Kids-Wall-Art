# Little Roots by Moodscape — Shopify↔Printify Personalization Stack
## Implementation Requirements (v2, corrected 2026-06-19)

> Saved verbatim from the build brief provided 2026-06-19. This is the source of truth for all components.
> See [Section 0](#0-output-accuracy-and-approval-gate-non-negotiable) for the non-negotiable approval gate.

This is the shared build brief for the personalized transliteration pipeline: a customer types a name in English, selects an Indian script, sees a live native-script preview, approves it, and checks out, after which the rendered print file is auto-submitted to Printify.

Architecture components (four deploy targets, mapped to folders in this repo):

- Component A — Transliteration engine → `service-render/` (IndicXlit, behind swappable interface)
- Component B — Shopify theme + Theme App Extension → `theme-extension/`
- Component C — Cloud Run rendering service (Python) → `service-render/`
- Component D — Shopify order webhook handler → `service-webhook/` (kept separate from C per repo-layout decision: D must ack fast and stay lightweight; C's container is heavy with Pillow/RAQM/IndicXlit weights/fonts)

Cross-cutting contract shared by B, service-render, and service-webhook lives in `shared/` (the `_script_payload` schema and the `transliterate()` interface) — see [shared/README.md](../shared/README.md).

---

## 0. Output Accuracy and Approval Gate (non-negotiable)

This is a customer's child's name on baby wall art, sold largely to South Asian families for naming ceremonies. A wrong native-script spelling is the single most trust-destroying failure this product can produce, and automated transliteration will mis-spell some names, because romanized Indian names are ambiguous (one English spelling maps to several valid native forms).

Therefore the pipeline is preview-and-approve, not fire-and-forget:

1. The customer must visually approve the final native-script rendering before checkout completes. The candidate picker (Component A) lets them choose among spellings; the rendered preview (Component C) shows the actual artwork.
2. The line-item property stores the customer-approved final artifact, not the raw English input. Store the chosen native-script string plus a reference (hash or upload id) to the exact rendered image the customer saw. The server must never re-transliterate from raw English at order time, because that can silently produce a different spelling than the one approved.
3. For the launch period, hold Printify submission for manual review. Component D should support a configurable hold so a native reader can eyeball each script before it goes to production. This can be relaxed to auto-submit once confidence is established per language.

Concretely, the cart line item should carry:

- `properties[Name in script]` — the customer-facing approved native-script string (visible at checkout).
- `properties[_script_payload]` — hidden JSON: `{ "input_en": "...", "script": "ta", "selected_native": "...", "render_id": "...", "render_hash": "..." }`.

Component D reads `_script_payload.render_id` / `render_hash` and reproduces the exact approved render. It does not re-derive the script.

**Design implication adopted (2026-06-19 decision):** Component C renders the approved image at preview time and persists it to a storage bucket (GCS or R2) keyed by `render_id`/`render_hash`. Component D's only job at order time is: verify HMAC, fetch the stored image, upload it to Printify, create the order, and ack fast — doing the Printify calls async (e.g. via Cloud Tasks) so a slow Printify response never blocks the webhook ack. This means D needs no font/render stack at all, and preview renders for carts that never convert are never uploaded to Printify.

---

## 1. Component A — Transliteration Engine

### 1.1 Recommended primary: self-hosted IndicXlit (AI4Bharat) in the Cloud Run service

Status: documented, open-source, actively maintained. Recommended as the authoritative engine.

AI4Bharat's IndicXlit is a neural English→native transliteration model distributed as the `ai4bharat-transliteration` PyPI package. It covers the scripts Little Roots sells: Tamil, Telugu, Hindi, Gujarati, Kannada, Malayalam, Marathi, Punjabi, Bengali, Urdu and others (14 languages total). It returns top-k candidates, so it can power the candidate picker directly.

Why this is the primary recommendation over the Google endpoint:

- It runs inside the existing Cloud Run Python container (Component C), the same environment already running Pillow/RAQM/HarfBuzz. No external API, no CORS proxy strictly required, no undocumented dependency that can disappear.
- It is Indic-specialized (built by AI4Bharat / IIT Madras) rather than a general transliteration service, so name accuracy is expected to be at least competitive for these scripts.
- Open source, CC BY-SA licensed model weights.

Implementation:

- Add `ai4bharat-transliteration` to the Cloud Run container's Python deps. Pre-download model weights into the image at build time (do not fetch at request time).
- Expose a `POST /transliterate` endpoint on the Cloud Run service: body `{ "text": "arjun", "lang": "ta", "topk": 5 }` → `{ "candidates": ["...","..."] }`.
- The PDP block (Component B) calls this endpoint for the live candidate list. Front it with the Cloudflare Worker for edge caching + CORS (the Worker's role shifts from "Google proxy" to "cache/CORS in front of our own service").

Validate empirically before committing:

- Model size and Cloud Run cold start. IndicXlit weights add meaningfully to image size and can slow cold starts. Set `min-instances >= 1` if the live preview must feel instant, and measure p95 latency per language.
- Candidate quality for names specifically. Build a test set of 50–100 real names per priority language and have a native reader score the top-1 and top-5 accuracy. This is your go/no-go per language.

Source (package + language coverage, accessed 2026-06-19): https://github.com/AI4Bharat/IndicNLP-Transliteration/releases · https://pypi.org/project/ai4bharat-transliteration/

### 1.2 Optional secondary candidate source: Google Input Tools (undocumented)

Status: unofficial, reverse-engineered. Use only as an optional enhancement, never as the sole dependency.

The `inputtools.google.com/request` endpoint returns a candidate list and is what many community clients use, but Google does not document or support it. Treat it as a nice-to-have that can be A/B'd against IndicXlit for candidate quality, behind the same swappable interface (1.4). If you wire it, keep it behind the Cloudflare Worker (CORS + caching) and never let a checkout-blocking path depend on it.

Observed (unofficial) contract:

- `GET https://inputtools.google.com/request?text=arjun&itc=hi-t-i0-und&num=5&cp=0&cs=1&ie=utf-8&oe=utf-8&app=test`
- Response shape: `["SUCCESS", [[ "arjun", ["अर्जुन","अरजुन",...], [], {} ]]]` — index 0 is the status string, index 1 is the result array.
- Unofficial ITC codes: `ta-t-i0-und` (Tamil), `hi-t-i0-und` (Hindi), `te-t-i0-und` (Telugu), `kn-t-i0-und` (Kannada), `ml-t-i0-und` (Malayalam), `bn-t-i0-und` (Bengali), `gu-t-i0-und` (Gujarati), `pu-t-i0-und` (Punjabi/Gurmukhi), `mr-t-i0-und` (Marathi), `or-t-i0-und` (Odia), `sa-t-i0-und` (Sanskrit), `ur-t-i0-und` (Urdu).
- No documented auth (currently none required), no documented rate limits, no CORS guarantees. Subject to change or shutdown without notice.

Sources (reverse-engineered, accessed 2026-06-19): community client `beginner1729/google-input-tools-api`; language table at https://github.com/sambhuWeb/google-input-tool/blob/master/Languages.md

### 1.3 Documented fallback: Google Cloud Translation v3 (Advanced)

Status: documented and billable, but Pre-GA for transliteration. Use as a degraded fallback, not primary.

Cloud Translation can transliterate romanized input directly into a target language's writing system by setting the transliteration config on the `translateText` method:

- `POST https://translation.googleapis.com/v3/projects/{PROJECT}/locations/{LOCATION}:translateText`
- Set `transliterationConfig` (`enableTransliteration: true`); source text must be romanized only.
- Requires the Advanced (v3) edition and service-account / IAM auth (not a bare API key).
- Returns a single result, not a candidate list, so it cannot drive the picker UX on its own.

Important caveats to confirm against the live docs:

- Transliteration is only on Cloud Translation Advanced and is a Pre-GA feature ("as is," limited support).
- The exact set of transliteration-supported languages is not enumerated on the method page; query `GET .../v3/projects/{PROJECT}/locations/{LOCATION}/supportedLanguages` and confirm each Little Roots script is covered before relying on this path.

Source (accessed 2026-06-19, page last updated 2026-06-09): https://cloud.google.com/translate/docs/basic/translating-text · language support: https://cloud.google.com/translate/docs/languages

### 1.4 Required: swappable transliteration interface

All three sources above must sit behind one internal interface so the backend is interchangeable without touching Components B or D:

```
transliterate(text: str, lang: str, topk: int) -> list[str]   # ranked candidates
```

Default implementation = IndicXlit (1.1). Optional implementations = Input Tools (1.2), Cloud Translation (1.3). The PDP block and webhook handler only ever see this interface. A shutdown or quality regression in any one source becomes a config change, not a rebuild.

### 1.5 Cannot confirm / validate empirically

- IndicXlit per-language name accuracy, model size impact on Cloud Run cold start, and p95 latency — measure.
- Input Tools endpoint stability, rate limits, CORS — undocumented, assume none.
- Cloud Translation transliteration language coverage for Indic scripts — confirm via `supportedLanguages`.

---

## 2. Component B — Shopify Storefront + Theme App Extension

The store runs a Dawn-based theme (`moodscape-pdp-breathing-room-v2`) on a standard (non-Plus) plan. Patch-only on the latest working theme zip; agents paste into the Shopify code editor, no production zip uploads.

### 2.1 `/cart/add.js` — adding variants with line-item properties

Status: official, stable.

- Endpoint: `POST /cart/add.js`. Accepts `application/json` and `application/x-www-form-urlencoded`.
- Required: `id` (variant ID, not product ID), `quantity`.
- Optional: `properties` (key/value object) or an `items` array for multiple lines.

Single-item JSON:

```json
{
  "id": 1234567890,
  "quantity": 1,
  "properties": {
    "Name in script": "அர்ஜுன்",
    "_script_payload": "{\"input_en\":\"arjun\",\"script\":\"ta\",\"selected_native\":\"அர்ஜுன்\",\"render_id\":\"...\",\"render_hash\":\"...\"}"
  }
}
```

`items[]` form (same fields per element) is also accepted. Error responses are JSON with `status`/`message`/`description` (the precise `/cart/add.js` success schema is not formally specified in the Ajax docs; rely on `GET /cart.js` for canonical cart state after add).

Source (accessed 2026-06-19): https://shopify.dev/docs/api/ajax/reference

### 2.2 Hidden underscore-prefixed properties

Status: official for the hidden-at-checkout behavior; order persistence is consistent in practice but inferred, not contractually stated.

A `properties[_script_payload]` input becomes `line_item.properties._script_payload`. The underscore hides it from the cart and checkout UI while keeping it on the line item, and underscore-prefixed properties do appear in `orders/create` webhook payloads under `line_items[].properties` (confirmed by Shopify staff examples; not a written guarantee). See Section 0 for what must go in this payload.

### 2.3 Reading the selected variant ID in the Dawn product form

Status: doc-aligned.

The product form posts a field named `id` whose value is the variant ID. Dawn keeps a hidden `input[name="id"]` in sync with the active variant via its `VariantSelects`/`VariantRadios` JS. The personalization block must read the selected variant from the existing `input[name="id"]` inside the main `{% form 'product', product %}` at the moment of add-to-cart. Do not introduce a new variant selector.

### 2.4 Theme App Extension — app block schema (CORRECTED)

Status: official; v1's schema used a deprecated attribute.

App block Liquid files live under `blocks/*.liquid` with a `{% schema %}`. For a PDP block:

- `target` must be `"section"` (app embed blocks use `"head"`, `"body"`, or `"compliance_head"`; those are for overlays/scripts, not inline PDP UI).
- Use `enabled_on` (or `disabled_on`), not the bare `templates` attribute. `enabled_on`/`disabled_on` replaced `templates`, and you may use only one of the two.

```json
{
  "name": "Little Roots Personalization",
  "target": "section",
  "enabled_on": { "templates": ["product"] },
  "settings": [
    { "type": "text", "id": "heading", "label": "Heading", "default": "Personalize this name print" }
  ]
}
```

The product-template section must opt in to app blocks:

```json
"blocks": [ { "type": "@app" }, { "type": "@theme" } ]
```

(If a top-level app block is added directly to a template, Shopify wraps it in an `apps.liquid` section; a custom `apps.liquid` must support `@app` blocks and include a preset.)

Source (accessed 2026-06-19): https://shopify.dev/docs/apps/build/online-store/theme-app-extensions/configuration · app blocks: https://shopify.dev/docs/storefronts/themes/architecture/blocks/app-blocks

### 2.5 Cannot confirm / recently changed

- Exact `/cart/add.js` success-response schema is not formally documented; treat `/cart.js` as canonical.
- Order persistence of underscore properties is observed and reliable but not a written contract.

---

## 3. Components C + D — Cloud Run Service (Printify + Webhooks + Rendering)

### 3.1 Printify Orders API — creating orders with custom `print_areas`

Status: official.

- Base: `https://api.printify.com/v1/`. Auth header: `Authorization: Bearer {PRINTIFY_API_TOKEN}`.
- Create order: `POST /v1/shops/{shop_id}/orders.json`.
- Top level: `external_id`, `label`, `line_items[]`, `shipping_method` (int), `address_to`, optional booleans (`is_printify_express`, `is_economy_shipping`, `send_shipping_notification`).
- For on-the-fly custom print config, each `line_items[]` element: `print_provider_id`, `blueprint_id`, `variant_id`, `quantity`, `print_areas`, optional `external_id`.
- `print_areas` maps a position key (e.g. `"front"`) to an array of placed-image objects: `{ "src": "...", "x": 0.5, "y": 0.5, "scale": 1.0, "angle": 0 }`. Position keys must match the blueprint's placeholder `position` values (see 3.2).

### 3.1a Image handling (ADDED)

Do not reference an arbitrary external URL in `print_areas[].src` and assume it stays reachable at production time. Upload the rendered PNG to Printify first and reference the returned upload. Printify's image upload endpoint (`POST /v1/uploads/images.json`, accepting a file URL or base64 contents and returning an id/preview) is the intended pattern; confirm the exact upload-then-reference contract and whether the orders endpoint also accepts direct external URLs against the live dev docs before finalizing. Store the returned upload id as the `render_id` referenced in Section 0.

### 3.2 Printify Products API — blueprint / provider / variants / placeholders

Status: official.

- `GET /v1/shops/{shop_id}/products/{product_id}.json` returns `blueprint_id`, `print_provider_id`, `variants[]` (each with `id` used as `variant_id` in orders), and `print_areas[]`.
- Each `print_areas[]` entry has `variant_ids[]` and `placeholders[]`; each placeholder has `position` (e.g. `"front"`), `height`, `width` (pixels), and optional `images[]`. Use `position` as the `print_areas` key when building orders, and the placeholder `height`/`width` to size the render canvas in Component C.

### 3.3 Auth and rate limits (CORRECTED)

Status: publishing limit and order-creation exemption are official; per-minute global/catalog figures are unconfirmed.

- Confirmed: product publishing is limited to 200 requests per 30 minutes, and product creation that results from order creation is not rate-limited. Error responses must stay under 5% of total requests or access can be restricted.
- The "600 requests/minute global" and "100/minute catalog" figures from v1 did not surface in the current official overview during verification. Do not hard-code those thresholds. Instead implement exponential backoff with jitter on every 429, plus a token-bucket throttle you can tune from config, and surface 429 rates in logging.

Source (accessed 2026-06-19): https://developers.printify.com/ · https://help.printify.com/hc/en-us/articles/29424311736465

### 3.4 Shopify `orders/create` webhook — reading personalization

Status: official.

The `orders/create` payload includes `line_items[]`, each with a `properties` object. Read the approved render reference from `line_items[].properties._script_payload` (Section 0). Underscore-prefixed keys are present here even though they are hidden in customer-facing UI.

### 3.5 Shopify webhook HMAC verification

Status: official.

- Header: `X-Shopify-Hmac-Sha256`.
- Compute HMAC-SHA256 over the raw request body bytes (read before any JSON parsing) using the webhook/app shared secret as the key, base64-encode, and compare to the header with a constant-time comparison. Reject on mismatch.

Source (accessed 2026-06-19): https://shopify.dev/docs/apps/build/webhooks/verify-deliveries

### 3.6 Shopify API version to target (CORRECTED note)

Status: official.

- 2026-04 is the current latest stable and the recommended production target; each stable version is supported ~12 months.
- Shopify ships a new version on the first of each quarter, so 2026-07 releases July 1, 2026 (about two weeks out from this doc). Re-evaluate then, but 2026-04 remains supported and safe.
- Always pin an explicit stable version in request URLs. Never target the release candidate or `unstable` channel in production, and never rely on Shopify's fall-forward default.

Source (accessed 2026-06-19): https://shopify.dev/docs/api/usage/versioning

### 3.7 Cannot confirm / validate empirically

- Printify `print_areas` coordinate system and units are not rigorously documented; calibrate per blueprint with test prints.
- Whether the orders endpoint accepts direct external `src` URLs vs. requiring a prior upload — confirm (see 3.1a).
- Exact Printify per-minute throttles beyond the documented publishing limit — handle via backoff, not hard-coded numbers.

---

## 4. Component C — Rendering Stack (Pillow + RAQM / HarfBuzz)

Status: official, stable. This is mandatory for correct Indic shaping (conjuncts, matras, ligatures). Naive `ImageDraw.text` without RAQM will render Indic scripts incorrectly.

- Pillow needs libraqm for complex text layout, which itself depends on FreeType, HarfBuzz, and FriBiDi.
- Detect at runtime: `PIL.features.check_feature("raqm")` must return `True`. Render with `layout_engine=ImageFont.Layout.RAQM`.
- Debian/Ubuntu (Cloud Run) system packages to install before/with Pillow:

```
libfreetype6-dev libharfbuzz-dev libfribidi-dev \
libjpeg-dev zlib1g-dev liblcms2-dev libwebp-dev libtiff5-dev libopenjp2-7-dev
```

- libraqm may need building from source (Meson/CMake) if not available as a prebuilt wheel dependency in the chosen base image. After build, gate startup on `check_feature("raqm") == True` so a misbuilt image fails fast instead of shipping broken glyphs.
- Bundle the actual Indic fonts (e.g. Noto Sans Tamil/Telugu/Devanagari/etc.) in the image; do not rely on system defaults.
- Pin and log the Pillow version at runtime (`python -c "import PIL; print(PIL.__version__)"`); the en/latest docs are versionless.

Source (accessed 2026-06-19): https://pillow.readthedocs.io/en/latest/installation/building-from-source.html

---

## 5. Quick Agent-Facing Checklist

**Component A — Transliteration**

- Primary: `ai4bharat-transliteration` (IndicXlit) in the Cloud Run container; expose `POST /transliterate` returning ranked candidates; cache/CORS via Cloudflare Worker.
- Optional candidate source: Input Tools endpoint (undocumented, never checkout-blocking).
- Fallback: Cloud Translation v3 Advanced (`transliterationConfig`, Pre-GA, single result, IAM auth).
- All behind one `transliterate(text, lang, topk)` interface.

**Component B — Theme + Extension**

- Add line item: `POST /cart/add.js`, fields `id` (variant), `quantity`, `properties`.
- Carry `properties[Name in script]` (visible) + `properties[_script_payload]` (hidden JSON with approved native string + render id/hash).
- Read selected variant from existing `input[name="id"]` in the Dawn product form.
- App block schema: `"target": "section"`, `"enabled_on": {"templates": ["product"]}` (NOT bare `templates`); section must allow `[{"type":"@app"},{"type":"@theme"}]`.

**Components C + D — Cloud Run**

- Printify: base `https://api.printify.com/v1/`, `Authorization: Bearer`, create order `POST /v1/shops/{shop_id}/orders.json`.
- `line_items[]`: `print_provider_id`, `blueprint_id`, `variant_id`, `quantity`, `print_areas` (`{src,x,y,scale,angle}`, keys = blueprint placeholder positions).
- Upload rendered PNG to Printify first (`POST /v1/uploads/images.json`); reference the returned upload, store its id as `render_id`.
- Rate limits: publishing 200/30min, order-driven creation exempt, <5% errors; otherwise exponential backoff on 429, no hard-coded per-minute caps.
- Webhook: read `line_items[].properties._script_payload`; verify HMAC-SHA256(base64) of raw body vs `X-Shopify-Hmac-Sha256`, constant-time.
- Pin Shopify API version 2026-04 (re-check after 2026-07-01); never RC/unstable.
- Rendering: Pillow + RAQM (`check_feature("raqm")==True`), libraqm/HarfBuzz/FreeType/FriBiDi, bundled Noto Indic fonts.

**Cross-cutting — Accuracy gate (Section 0)**

- Customer approves the rendered preview before checkout.
- Server reproduces the approved render by id/hash; never re-transliterates from raw English at order time.
- Launch period: manual hold on Printify submission for native-reader review.

## Changelog (v1 → v2)

1. Transliteration backend (Section 1). Replaced "Cloudflare Worker proxy to an undocumented Google endpoint" as the primary path with self-hosted IndicXlit in the Cloud Run container, covering all Little Roots scripts with no external dependency. Input Tools demoted to optional; Cloud Translation v3 added as a documented (Pre-GA) fallback. All three placed behind one swappable interface.
2. App block schema (Section 2.4). Corrected deprecated `"templates": ["product"]` to `"enabled_on": {"templates": ["product"]}`.
3. Printify rate limits (Section 3.3). Dropped the unconfirmed 600/min and 100/min figures; kept the documented 200/30min publishing limit and added the order-creation exemption; mandated backoff-on-429 instead of hard-coded caps.
4. Shopify API version (Section 3.6). Confirmed 2026-04 as current latest stable; flagged the 2026-07 release on July 1 and the rule against RC/unstable in production.
5. Added — Accuracy and approval gate (Section 0). Customer-approved render must be the stored artifact; no server-side re-transliteration at order time; manual hold for launch.
6. Added — Printify image handling (Section 3.1a). Upload rendered PNG to Printify and reference the upload rather than trusting an external URL.

## Repo layout decision (2026-06-19)

Single monorepo, lightly structured, one folder per deploy target:

```
little-roots/
  worker/            Cloudflare Worker (TS, wrangler)
  theme-extension/   Shopify theme app extension (Liquid/JS, shopify CLI)
  service-render/    Cloud Run: transliterate + render (Python) — Components A + C
  service-webhook/   Cloud Run: order webhook handler (Python) — Component D
  shared/            _script_payload schema, transliterate contract, fixtures
  docs/              this spec, acceptance criteria
```

C and D are kept as separate Cloud Run services (not combined) because they have opposite runtime profiles: D must ack Shopify's webhook within seconds (missed ack → Shopify retries → duplicate Printify orders), while C's container is heavy (Pillow, libraqm, HarfBuzz, IndicXlit weights, bundled Noto fonts) with slower cold starts. Splitting keeps the webhook handler tiny/fast and isolates order integrity from render bugs.

D needs no font/render stack: C renders the approved image at preview time and persists it to a storage bucket (GCS or R2) keyed by `render_id`/`render_hash`; D's only job is verify HMAC → fetch stored image → upload to Printify → create order → ack fast (Printify calls done async via Cloud Tasks so a slow Printify response never blocks the webhook ack).

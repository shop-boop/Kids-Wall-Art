# theme-extension/ — Component B

Shopify Theme App Extension for the Little Roots PDP personalization block.

## Files

- [`shopify.extension.toml`](shopify.extension.toml) — extension manifest.
- [`blocks/little-roots-personalization.liquid`](blocks/little-roots-personalization.liquid) —
  the app block. Schema uses `"target": "section"` + `"enabled_on"` (spec
  2.4's corrected form — NOT the deprecated bare `"templates"` attribute).
- [`assets/little-roots.js`](assets/little-roots.js) — candidate picker,
  preview, approval gate, and `/cart/add.js` integration. Reads the
  variant id from the theme's existing `input[name="id"]` (spec 2.3) rather
  than adding a second selector.
- [`assets/little-roots.css`](assets/little-roots.css) — minimal styling.
- [`locales/en.default.json`](locales/en.default.json) — UI strings.

## UPDATE ME before this works end-to-end

1. **`render_endpoint` block setting** — set to the deployed Cloudflare
   Worker URL (see [../worker/](../worker/)) in the theme editor once this
   block is added to the PDP.
2. **Canvas dimensions in `assets/little-roots.js`** (`selectCandidate`) —
   currently hard-coded `1200x1200`; pull the real Printify blueprint
   placeholder `width`/`height` (spec 3.2) for the selected variant instead.
3. **Cart redirect** in `addToCartWithPersonalization` — currently a hard
   redirect to `/cart`; replace with this store's actual cart-drawer
   convention (the Dawn theme in use is `moodscape-pdp-breathing-room-v2` —
   check its existing add-to-cart JS for the convention it already uses).
4. **Preview image URL** returned by `/render` — confirm `service-render`'s
   storage backend returns a publicly fetchable HTTPS URL, not a `gs://` or
   `r2://` URI (see [../service-render/app/storage.py](../service-render/app/storage.py)).

## Required theme-side patch (NOT part of this extension — apply by hand)

Per spec 2.4, the product template's section must opt in to app blocks.
This repo cannot patch the Dawn theme directly (theme code lives in the
Shopify code editor, not here). In the **Shopify admin → Online Store →
Edit code**, find the product section (e.g. `sections/main-product.liquid`)
and ensure its schema's `blocks` array includes:

```json
"blocks": [
  { "type": "@app" },
  { "type": "@theme" }
]
```

If `@app` is missing, the Little Roots block won't be selectable in the
theme editor's block list for that section. Do not upload a new theme zip —
paste this change into the existing section file per the project's
patch-only convention.

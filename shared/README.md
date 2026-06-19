# shared/

Cross-cutting contracts imported by both `service-render` and `service-webhook`
(and mirrored in JS in `theme-extension` — keep the two in sync by hand since
the theme runs in Liquid/JS, not Python).

- [`script_payload.py`](script_payload.py) — the `_script_payload` hidden
  cart line-item property schema (see [docs/spec-v2.md](../docs/spec-v2.md)
  Section 0). `service-render` produces it after a render; `service-webhook`
  consumes it and must never re-derive the script from `input_en`.
- [`transliterate_interface.py`](transliterate_interface.py) — the
  `TransliteratorBackend` ABC (spec Section 1.4). All transliteration
  backends (IndicXlit, Input Tools, Cloud Translation) implement this so the
  HTTP layer in `service-render` is interchangeable via config.

Both services install this folder as a local editable dependency (see each
service's `pyproject.toml` / `requirements.txt`).

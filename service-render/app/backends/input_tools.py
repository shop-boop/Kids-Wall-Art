"""Optional secondary candidate source: undocumented Google Input Tools
endpoint (spec 1.2). Never used on a checkout-blocking path — only as an
optional A/B enhancement alongside IndicXlit.
"""
from __future__ import annotations

import httpx

from transliterate_interface import TransliteratorBackend

# Unofficial ITC codes (spec 1.2). UPDATE ME if Google changes these without notice.
_ITC_CODES = {
    "ta": "ta-t-i0-und",
    "hi": "hi-t-i0-und",
    "te": "te-t-i0-und",
    "kn": "kn-t-i0-und",
    "ml": "ml-t-i0-und",
    "bn": "bn-t-i0-und",
    "gu": "gu-t-i0-und",
    "pa": "pu-t-i0-und",
    "mr": "mr-t-i0-und",
    "ur": "ur-t-i0-und",
}

_ENDPOINT = "https://inputtools.google.com/request"


class InputToolsBackend(TransliteratorBackend):
    def __init__(self, timeout_s: float = 3.0) -> None:
        self._timeout_s = timeout_s

    def transliterate(self, text: str, lang: str, topk: int = 5) -> list[str]:
        itc = _ITC_CODES.get(lang)
        if itc is None or not text.strip():
            return []

        params = {
            "text": text,
            "itc": itc,
            "num": topk,
            "cp": 0,
            "cs": 1,
            "ie": "utf-8",
            "oe": "utf-8",
            "app": "test",
        }
        try:
            resp = httpx.get(_ENDPOINT, params=params, timeout=self._timeout_s)
            resp.raise_for_status()
            payload = resp.json()
        except (httpx.HTTPError, ValueError):
            # Undocumented endpoint, no uptime guarantee — fail soft, never raise.
            return []

        if not payload or payload[0] != "SUCCESS":
            return []
        try:
            candidates = payload[1][0][1]
        except (IndexError, TypeError):
            return []
        return list(candidates)[:topk]

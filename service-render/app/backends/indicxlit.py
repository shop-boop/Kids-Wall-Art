"""Primary transliteration backend: self-hosted AI4Bharat IndicXlit (spec 1.1).

Model weights must be pre-downloaded into the container image at build time
(see ../../Dockerfile) — never fetch them at request time.
"""
from __future__ import annotations

import logging

from transliterate_interface import TransliteratorBackend

logger = logging.getLogger(__name__)

# Lang codes IndicXlit expects vs. our spec's script codes happen to match
# (ta, te, hi, gu, kn, ml, mr, pa, bn, ur) per the ai4bharat-transliteration
# package's documented language coverage. Confirm against the installed
# package version if this ever drifts.
_SUPPORTED = {"ta", "te", "hi", "gu", "kn", "ml", "mr", "pa", "bn", "ur"}


class IndicXlitBackend(TransliteratorBackend):
    def __init__(self) -> None:
        self._engine = None  # lazy-loaded on first use to keep import-time cheap

    def _load(self):
        if self._engine is None:
            # UPDATE ME: confirm exact import path/API against the installed
            # ai4bharat-transliteration version; this mirrors the package's
            # documented usage as of 2026-06-19.
            from ai4bharat.transliteration import XlitEngine  # type: ignore

            self._engine = XlitEngine(beam_width=10, rescore=True)
        return self._engine

    def transliterate(self, text: str, lang: str, topk: int = 5) -> list[str]:
        if lang not in _SUPPORTED:
            raise ValueError(f"IndicXlit does not cover script {lang!r}")
        if not text.strip():
            return []

        engine = self._load()
        result = engine.translit_word(text, lang_code=lang, topk=topk)
        # translit_word returns {lang_code: [candidates...]} per package docs;
        # UPDATE ME if the installed version's return shape differs.
        candidates = result.get(lang, []) if isinstance(result, dict) else result
        return list(candidates)[:topk]

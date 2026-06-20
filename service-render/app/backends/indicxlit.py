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
            from ai4bharat.transliteration import XlitEngine  # type: ignore

            # rescore=True needs an extra LM dependency not exercised here;
            # confirmed empirically (2026-06-19, ai4bharat-transliteration
            # 1.1.3) that beam_width=4, rescore=False returns clean ranked
            # candidates without it.
            self._engine = XlitEngine(beam_width=4, rescore=False)
        return self._engine

    def transliterate(self, text: str, lang: str, topk: int = 5) -> list[str]:
        if lang not in _SUPPORTED:
            raise ValueError(f"IndicXlit does not cover script {lang!r}")
        if not text.strip():
            return []

        engine = self._load()
        # Confirmed empirically (2026-06-19): translit_word returns a plain
        # list[str], not {lang_code: [...]} as the package's own docs imply.
        # Each candidate carries a trailing U+200C (zero-width non-joiner)
        # that must be stripped before it's ever stored/displayed/hashed —
        # otherwise the customer-visible string and the stored render won't
        # byte-match later (spec Section 0's accuracy gate depends on exact
        # string fidelity).
        candidates = engine.translit_word(text, lang_code=lang, topk=topk)
        return [c.replace("\u200c", "") for c in candidates][:topk]

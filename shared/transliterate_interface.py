"""Swappable transliteration interface (spec Section 1.4).

service-render's HTTP layer and any future backend implementation must
depend only on this ABC, never on a specific engine. Default impl =
IndicXlit; optional impls = Input Tools, Cloud Translation v3.
"""
from __future__ import annotations

from abc import ABC, abstractmethod


class TransliteratorBackend(ABC):
    """transliterate(text, lang, topk) -> ranked list of native-script candidates."""

    @abstractmethod
    def transliterate(self, text: str, lang: str, topk: int = 5) -> list[str]:
        """Return up to `topk` ranked native-script candidates for `text` in `lang`.

        Must never raise on empty results — return [] instead. Callers (the PDP
        candidate picker) treat an empty list as "no suggestion available."
        """
        raise NotImplementedError

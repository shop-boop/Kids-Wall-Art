"""Backend registry — the only place that maps a config string to an implementation."""
from __future__ import annotations

from transliterate_interface import TransliteratorBackend

from app.config import TRANSLITERATE_BACKEND


def get_backend() -> TransliteratorBackend:
    if TRANSLITERATE_BACKEND == "indicxlit":
        from .indicxlit import IndicXlitBackend

        return IndicXlitBackend()
    if TRANSLITERATE_BACKEND == "input_tools":
        from .input_tools import InputToolsBackend

        return InputToolsBackend()
    if TRANSLITERATE_BACKEND == "cloud_translation":
        from .cloud_translation import CloudTranslationBackend

        return CloudTranslationBackend()
    raise ValueError(f"unknown TRANSLITERATE_BACKEND: {TRANSLITERATE_BACKEND!r}")

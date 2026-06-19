"""Documented fallback: Google Cloud Translation v3 Advanced transliteration
(spec 1.3). Pre-GA, single result (not a candidate list), IAM auth.

UPDATE ME: confirm GCP_PROJECT_ID in app/config.py and that the target
script is listed under `supportedLanguages` for your project before relying
on this path in production.
"""
from __future__ import annotations

from transliterate_interface import TransliteratorBackend
from app.config import GCP_PROJECT_ID, GCP_LOCATION


class CloudTranslationBackend(TransliteratorBackend):
    def __init__(self) -> None:
        self._client = None

    def _load(self):
        if self._client is None:
            from google.cloud import translate  # type: ignore

            self._client = translate.TranslationServiceClient()
        return self._client

    def transliterate(self, text: str, lang: str, topk: int = 5) -> list[str]:
        if not text.strip():
            return []

        client = self._load()
        parent = f"projects/{GCP_PROJECT_ID}/locations/{GCP_LOCATION}"
        response = client.translate_text(
            request={
                "parent": parent,
                "contents": [text],
                "mime_type": "text/plain",
                "target_language_code": lang,
                "transliteration_config": {"enable_transliteration": True},
            }
        )
        # Returns a single result, not ranked candidates (spec 1.3) — pad to
        # a one-element list so callers always get list[str].
        translations = getattr(response, "translations", [])
        if not translations:
            return []
        return [translations[0].translated_text]

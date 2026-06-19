"""Shared `_script_payload` contract.

This is the single source of truth for the hidden cart line-item property
`properties[_script_payload]` (see docs/spec-v2.md Section 0). Both
service-render (which produces it) and service-webhook (which consumes it)
import this module — do not redefine the shape elsewhere.

Per spec Section 0: the server must NEVER re-transliterate from raw English
at order time. service-webhook reads render_id/render_hash and fetches the
already-rendered, customer-approved image; it does not call transliterate().
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass


SUPPORTED_SCRIPTS = (
    "ta",  # Tamil
    "te",  # Telugu
    "hi",  # Hindi
    "gu",  # Gujarati
    "kn",  # Kannada
    "ml",  # Malayalam
    "mr",  # Marathi
    "pa",  # Punjabi
    "bn",  # Bengali
    "ur",  # Urdu
)


@dataclass(frozen=True)
class ScriptPayload:
    input_en: str
    script: str  # one of SUPPORTED_SCRIPTS
    selected_native: str
    render_id: str
    render_hash: str

    def __post_init__(self) -> None:
        if self.script not in SUPPORTED_SCRIPTS:
            raise ValueError(f"unsupported script code: {self.script!r}")
        if not self.input_en or not self.selected_native:
            raise ValueError("input_en and selected_native must be non-empty")
        if not self.render_id or not self.render_hash:
            raise ValueError("render_id and render_hash must be non-empty")

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, separators=(",", ":"))

    @classmethod
    def from_json(cls, raw: str) -> "ScriptPayload":
        data = json.loads(raw)
        try:
            return cls(
                input_en=data["input_en"],
                script=data["script"],
                selected_native=data["selected_native"],
                render_id=data["render_id"],
                render_hash=data["render_hash"],
            )
        except KeyError as exc:
            raise ValueError(f"_script_payload missing required field: {exc}") from exc

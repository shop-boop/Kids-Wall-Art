"""Indic-script rendering: Pillow + RAQM/HarfBuzz (spec Section 4).

Gates startup on PIL.features.check_feature("raqm") so a misbuilt image
fails fast instead of shipping broken glyphs. See Dockerfile for the
system packages RAQM needs.
"""
from __future__ import annotations

import hashlib
import io
import os

from PIL import Image, ImageDraw, ImageFont, features

from app.config import FONT_DIR, SCRIPT_FONT_MAP


def assert_raqm_available() -> None:
    if not features.check_feature("raqm"):
        raise RuntimeError(
            "Pillow built without RAQM support — Indic conjuncts/matras will "
            "render incorrectly. Fix the container build (see Dockerfile); "
            "refusing to start."
        )


def render_native_text(
    text: str,
    script: str,
    *,
    canvas_width: int,
    canvas_height: int,
    font_size: int = 96,
    text_color: tuple[int, int, int, int] = (20, 20, 20, 255),
) -> bytes:
    """Render `text` (already in native script) onto a transparent PNG canvas.

    canvas_width/canvas_height should come from the Printify blueprint
    placeholder's width/height (spec 3.2) — caller's responsibility.
    Returns raw PNG bytes.
    """
    assert_raqm_available()

    font_filename = SCRIPT_FONT_MAP.get(script)
    if font_filename is None:
        raise ValueError(f"no bundled font configured for script {script!r}")

    font_path = os.path.join(FONT_DIR, font_filename)
    if not os.path.exists(font_path):
        raise FileNotFoundError(
            f"font {font_filename!r} not found at {font_path} — UPDATE ME: "
            f"bundle real Noto Indic fonts into service-render/fonts/ (see "
            f"fonts/README.md)"
        )

    font = ImageFont.truetype(font_path, font_size, layout_engine=ImageFont.Layout.RAQM)

    image = Image.new("RGBA", (canvas_width, canvas_height), (255, 255, 255, 0))
    draw = ImageDraw.Draw(image)

    bbox = draw.textbbox((0, 0), text, font=font)
    text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    position = ((canvas_width - text_w) / 2 - bbox[0], (canvas_height - text_h) / 2 - bbox[1])

    draw.text(position, text, font=font, fill=text_color)

    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


def render_hash(png_bytes: bytes) -> str:
    """Content hash stored in _script_payload.render_hash (spec Section 0) —
    lets service-webhook verify it's fetching exactly the bytes the customer approved."""
    return hashlib.sha256(png_bytes).hexdigest()

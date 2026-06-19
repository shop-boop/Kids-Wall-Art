"""service-render: Components A (transliteration) + C (Indic rendering).

Endpoints:
  POST /transliterate  -> ranked native-script candidates
  POST /render          -> render approved candidate, persist, return render_id/hash
  GET  /healthz         -> startup gate, fails if RAQM missing
"""
from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from script_payload import SUPPORTED_SCRIPTS
from app.backends import get_backend
from app.config import CORS_ALLOWED_ORIGIN
from app.rendering import assert_raqm_available, render_hash, render_native_text
from app.storage import get_storage, new_render_id

logger = logging.getLogger("service-render")

app = FastAPI(title="little-roots-service-render")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[CORS_ALLOWED_ORIGIN],
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)

_backend = None


@app.on_event("startup")
def on_startup() -> None:
    assert_raqm_available()
    global _backend
    _backend = get_backend()
    logger.info("service-render started with backend=%s", _backend.__class__.__name__)


class TransliterateRequest(BaseModel):
    text: str
    lang: str
    topk: int = 5


class TransliterateResponse(BaseModel):
    candidates: list[str]


class RenderRequest(BaseModel):
    selected_native: str
    script: str
    input_en: str
    canvas_width: int
    canvas_height: int


class RenderResponse(BaseModel):
    render_id: str
    render_hash: str
    url: str


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}


@app.post("/transliterate", response_model=TransliterateResponse)
def transliterate(req: TransliterateRequest) -> TransliterateResponse:
    if req.lang not in SUPPORTED_SCRIPTS:
        raise HTTPException(status_code=400, detail=f"unsupported script: {req.lang}")
    candidates = _backend.transliterate(req.text, req.lang, req.topk)
    return TransliterateResponse(candidates=candidates)


@app.post("/render", response_model=RenderResponse)
def render(req: RenderRequest) -> RenderResponse:
    """Renders the customer-approved candidate (never raw English — see spec
    Section 0) and persists it so service-webhook can fetch the exact bytes
    the customer saw, by render_id, with no re-transliteration at order time."""
    if req.script not in SUPPORTED_SCRIPTS:
        raise HTTPException(status_code=400, detail=f"unsupported script: {req.script}")

    png_bytes = render_native_text(
        req.selected_native,
        req.script,
        canvas_width=req.canvas_width,
        canvas_height=req.canvas_height,
    )
    rid = new_render_id()
    digest = render_hash(png_bytes)
    url = get_storage().put(rid, png_bytes)

    return RenderResponse(render_id=rid, render_hash=digest, url=url)

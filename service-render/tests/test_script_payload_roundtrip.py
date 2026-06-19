"""Smoke test that service-render's render output is consumable by the
shared ScriptPayload contract (the boundary the repo-layout decision flagged
as the riskiest integration point)."""
from script_payload import ScriptPayload


def test_roundtrip():
    payload = ScriptPayload(
        input_en="arjun",
        script="ta",
        selected_native="அர்ஜுன்",
        render_id="abc123",
        render_hash="deadbeef",
    )
    raw = payload.to_json()
    restored = ScriptPayload.from_json(raw)
    assert restored == payload


def test_rejects_unsupported_script():
    import pytest

    with pytest.raises(ValueError):
        ScriptPayload(
            input_en="arjun",
            script="zz",
            selected_native="x",
            render_id="r",
            render_hash="h",
        )

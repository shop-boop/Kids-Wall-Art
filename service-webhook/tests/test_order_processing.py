import hashlib

import pytest

from app.order_processing import ManualHoldRequired, process_line_item
from script_payload import ScriptPayload


class FakeStorage:
    def __init__(self, bytes_by_id):
        self._bytes = bytes_by_id

    def get(self, render_id):
        return self._bytes[render_id]


def test_manual_hold_blocks_printify_submission(monkeypatch):
    png_bytes = b"fake-png-bytes"
    payload = ScriptPayload(
        input_en="arjun",
        script="ta",
        selected_native="அர்ஜுன்",
        render_id="rid1",
        render_hash=hashlib.sha256(png_bytes).hexdigest(),
    )

    monkeypatch.setattr("app.order_processing.get_storage", lambda: FakeStorage({"rid1": png_bytes}))
    monkeypatch.setattr("app.order_processing.MANUAL_HOLD_ENABLED", True)

    with pytest.raises(ManualHoldRequired):
        process_line_item(
            shopify_order_id="order1",
            line_item_properties={"_script_payload": payload.to_json()},
            printify_print_provider_id=1,
            printify_blueprint_id=2,
            printify_variant_id=3,
            quantity=1,
            address_to={},
        )


def test_hash_mismatch_blocks_submission(monkeypatch):
    stored_bytes = b"different-bytes-than-approved"
    payload = ScriptPayload(
        input_en="arjun",
        script="ta",
        selected_native="அர்ஜுன்",
        render_id="rid1",
        render_hash=hashlib.sha256(b"approved-bytes").hexdigest(),
    )

    monkeypatch.setattr("app.order_processing.get_storage", lambda: FakeStorage({"rid1": stored_bytes}))
    monkeypatch.setattr("app.order_processing.MANUAL_HOLD_ENABLED", False)

    with pytest.raises(ValueError, match="render_hash mismatch"):
        process_line_item(
            shopify_order_id="order1",
            line_item_properties={"_script_payload": payload.to_json()},
            printify_print_provider_id=1,
            printify_blueprint_id=2,
            printify_variant_id=3,
            quantity=1,
            address_to={},
        )

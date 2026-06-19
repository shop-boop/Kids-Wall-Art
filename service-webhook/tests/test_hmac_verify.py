import base64
import hashlib
import hmac

from app.hmac_verify import verify_shopify_hmac


def _sign(body: bytes, secret: str) -> str:
    digest = hmac.new(secret.encode(), body, hashlib.sha256).digest()
    return base64.b64encode(digest).decode()


def test_valid_hmac_passes():
    body = b'{"id": 123}'
    secret = "shh"
    header = _sign(body, secret)
    assert verify_shopify_hmac(body, header, secret) is True


def test_tampered_body_fails():
    body = b'{"id": 123}'
    secret = "shh"
    header = _sign(body, secret)
    assert verify_shopify_hmac(b'{"id": 999}', header, secret) is False


def test_missing_header_fails():
    assert verify_shopify_hmac(b"x", None, "shh") is False

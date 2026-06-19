"""Maps a Shopify variant ID to its Printify product/blueprint identifiers.

The spec doesn't define this mapping (it's store-catalog-specific, not a
documented API contract) — UPDATE ME: populate this once the Little Roots
Printify catalog is set up, by calling
GET /v1/shops/{shop_id}/products/{product_id}.json (spec 3.2) for each
product and recording blueprint_id/print_provider_id/variant_id per
Shopify variant.
"""
from __future__ import annotations

# UPDATE ME: Shopify variant_id (str) -> Printify identifiers
SHOPIFY_VARIANT_TO_PRINTIFY: dict[str, dict] = {
    # "UPDATE_ME_shopify_variant_id": {
    #     "print_provider_id": 0,
    #     "blueprint_id": 0,
    #     "variant_id": 0,
    # },
}


def lookup(shopify_variant_id: str) -> dict:
    mapping = SHOPIFY_VARIANT_TO_PRINTIFY.get(shopify_variant_id)
    if mapping is None:
        raise KeyError(
            f"no Printify mapping for Shopify variant {shopify_variant_id!r} — "
            f"UPDATE ME in app/variant_mapping.py"
        )
    return mapping

"""Shopify wire protocol constants, never merchant/deployment configuration."""

SHOP_PATTERN = r"^[a-z0-9][a-z0-9-]{0,62}\.myshopify\.com$"
AUTHORIZE_PATH = "/admin/oauth/authorize"
OAUTH_EXCHANGE_PATH = "/admin/oauth/access_token"
GRAPHQL_PATH = "/admin/api/{version}/graphql.json"
PRODUCT_GID_PREFIX = "gid://shopify/Product/"
VARIANT_GID_PREFIX = "gid://shopify/ProductVariant/"
SUPPORTED_TOPICS = {"products/create", "products/update", "products/delete", "app/uninstalled"}


def connector_owned_id(value: str) -> bool:
    """Reserved persisted namespace; manual imports must never overwrite these IDs."""
    return value.startswith("shopify_")

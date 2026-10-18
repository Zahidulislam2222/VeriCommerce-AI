"""Real PostgreSQL account/RBAC and fake-provider Shopify HTTP contract flows."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import sys
import time
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

import httpx
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import SecretStr
from vericommerce_core.database import transaction
from vericommerce_core.security import token_hash
from vericommerce_core.shopify_client import ShopifyClient, encrypted

PASSWORD = "test-password-long-enough"
SHOP = "test-fixture.myshopify.com"


@pytest.fixture(autouse=True)
def isolated_fake_store(monkeypatch: Any) -> None:
    monkeypatch.setattr(sys.modules[__name__], "SHOP", f"test-{uuid4().hex}.myshopify.com")


def browser(settings: Any) -> TestClient:
    from vericommerce_core.main import create_app

    return TestClient(
        create_app(settings), base_url="https://testserver", headers={"Origin": "https://testserver"}
    )


def register(client: TestClient) -> dict[str, Any]:
    email = f"test-{uuid4().hex}@example.test"
    response = client.post(
        "/api/auth/register",
        json={"email": email, "password": PASSWORD, "tenant_name": "Test merchant workspace"},
    )
    assert response.status_code == 200, response.text
    return dict(response.json())


def configured(settings: Any) -> Any:
    return settings.model_copy(
        update={
            "account_attempts_per_hour": 1000,
            "shopify_enabled": True,
            "shopify_client_id": "test-client-id",
            "shopify_client_secret": SecretStr("test-shopify-secret"),
            "shopify_encryption_key": SecretStr(base64.urlsafe_b64encode(b"test-key" * 4).decode()),
            "shopify_redirect_uri": "https://testserver/api/shopify/callback",
            "shopify_return_url": "https://testserver/engine#connections",
            "shopify_retry_seconds": 0,
            "shopify_max_retry_seconds": 0,
        }
    )


def provider_response(payload: dict[str, Any], version: str) -> httpx.Response:
    return httpx.Response(200, json=payload, headers={"X-Shopify-API-Version": version})


def product(updated: str | None = None) -> dict[str, Any]:
    return {
        "id": "gid://shopify/Product/123",
        "title": "Test product",
        "description": "Copper fixture",
        "productType": "Test category",
        "updatedAt": updated or datetime.now(UTC).isoformat(),
        "variants": {
            "nodes": [
                {
                    "id": "gid://shopify/ProductVariant/321",
                    "sku": "test-sku",
                    "title": "Default",
                    "selectedOptions": [{"name": "Color", "value": "Copper"}],
                }
            ],
            "pageInfo": {"hasNextPage": False},
        },
        "media": {
            "nodes": [{"id": "gid://shopify/MediaImage/456", "alt": "Test alt", "mediaContentType": "IMAGE"}],
            "pageInfo": {"hasNextPage": False},
        },
    }


def install_provider(
    client: TestClient, settings: Any, responses: list[dict[str, Any]] | None = None
) -> list[Any]:
    calls: list[Any] = []
    pages = list(
        responses or [{"data": {"products": {"nodes": [product()], "pageInfo": {"hasNextPage": False}}}}]
    )

    def fake(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        assert request.url.scheme == "https" and request.url.host == SHOP
        payload = json.loads(request.content)
        if request.url.path.endswith("/oauth/access_token"):
            assert payload["client_secret"] == "test-shopify-secret"
            return httpx.Response(
                200,
                json={
                    "access_token": "test-access-token",
                    "refresh_token": "test-refresh-token",
                    "scope": "read_products",
                    "expires_in": 3600,
                    "refresh_token_expires_in": 86400,
                },
            )
        assert payload["query"].startswith("query ") and "mutation" not in payload["query"].lower()
        assert request.headers["X-Shopify-Access-Token"] == "test-access-token"
        if "VeriCommerceShop " in payload["query"]:
            return provider_response(
                {"data": {"shop": {"id": "gid://shopify/Shop/42", "myshopifyDomain": SHOP}}},
                settings.shopify_api_version,
            )
        return provider_response(pages.pop(0), settings.shopify_api_version)

    client.app.state.shopify_transport = httpx.MockTransport(fake)  # type: ignore[union-attr]
    return calls


def oauth(client: TestClient, settings: Any) -> tuple[str, dict[str, str]]:
    response = client.post("/api/shopify/connect", json={"shop": SHOP})
    assert response.status_code == 200, response.text
    url = response.json()["authorization_url"]
    params = {
        "shop": SHOP,
        "code": "test-authorization-code",
        "timestamp": str(int(time.time())),
        "state": parse_qs(urlsplit(url).query)["state"][0],
    }
    message = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    params["hmac"] = hmac.new(b"test-shopify-secret", message.encode(), hashlib.sha256).hexdigest()
    return url, params


def connect(client: TestClient, settings: Any) -> None:
    _, params = oauth(client, settings)
    response = client.get("/api/shopify/callback", params=params, follow_redirects=False)
    assert response.status_code == 303, response.text
    assert response.headers["location"] == settings.shopify_return_url
    assert response.headers["Referrer-Policy"] == "no-referrer"


def webhook(
    client: TestClient,
    topic: str,
    payload: dict[str, Any],
    *,
    event: str | None = None,
    at: datetime | None = None,
    valid: bool = True,
) -> httpx.Response:
    raw = json.dumps(payload, separators=(",", ":")).encode()
    signature = base64.b64encode(hmac.new(b"test-shopify-secret", raw, hashlib.sha256).digest()).decode()
    return client.post(
        "/api/shopify/webhook",
        content=raw,
        headers={
            "Origin": "https://untrusted.example.test",
            "Sec-Fetch-Site": "cross-site",
            "Content-Type": "application/octet-stream",
            "X-Shopify-Hmac-Sha256": signature if valid else "test-invalid",
            "X-Shopify-Shop-Domain": SHOP,
            "X-Shopify-Topic": topic,
            "X-Shopify-Webhook-Id": event or str(uuid4()),
            "X-Shopify-Triggered-At": (at or datetime.now(UTC)).isoformat(),
        },
    )


def test_account_cookie_rotation_logout_and_demo_isolation(settings: Any) -> None:
    config = settings.model_copy(update={"account_attempts_per_hour": 1000})
    with browser(config) as client:
        assert client.get("/api/version").json()["version"] == config.api_version
        assert client.get("/api/auth/me").json()["authenticated"] is False
        assert client.get("/api/products").status_code == 401
        demo = client.post("/api/session", json={}).json()["tenant_id"]
        account = register(client)
        merchant = account["active_tenant_id"]
        assert merchant != demo
        assert client.get("/api/session").json()["demo"] is False
        assert client.get("/api/products").json()["products"] == []
        original = client.cookies.get(config.account_cookie_name)
        assert original
        response = client.post(
            "/api/auth/login", json={"email": account["user"]["email"], "password": PASSWORD}
        )
        assert response.status_code == 200
        assert client.cookies.get(config.account_cookie_name) != original
        cookie = response.headers["set-cookie"].lower()
        assert "httponly" in cookie and "secure" in cookie and "samesite=strict" in cookie
        with transaction(config) as db:
            assert not db.execute(
                "SELECT 1 FROM account_sessions WHERE token_hash=%s", (token_hash(original),)
            ).fetchone()
            row = db.execute(
                "SELECT password_hash FROM accounts WHERE id=%s", (account["user"]["id"],)
            ).fetchone()
            assert row and PASSWORD not in row["password_hash"] and row["password_hash"].startswith("scrypt$")
        token = client.cookies.get(config.account_cookie_name)
        assert client.post("/api/auth/logout", json={}).status_code == 200
        with transaction(config) as db:
            assert not db.execute(
                "SELECT 1 FROM account_sessions WHERE token_hash=%s", (token_hash(token or ""),)
            ).fetchone()
            assert db.execute(
                "SELECT 1 FROM demo_sessions WHERE tenant_id=%s AND mode='merchant' "
                "AND expires_at='infinity'",
                (merchant,),
            ).fetchone()


def test_four_role_matrix_membership_revalidation_and_cross_tenant(settings: Any) -> None:
    config = settings.model_copy(update={"account_attempts_per_hour": 1000})
    clients = [browser(config) for _ in range(4)]
    try:
        identities = [register(c) for c in clients]
        owner = clients[0]
        tenant = identities[0]["active_tenant_id"]
        assert (
            owner.patch(
                "/api/auth/members", json={"account_id": identities[0]["user"]["id"], "role": "viewer"}
            ).status_code
            == 409
        )
        for client, identity, role in zip(
            clients[1:], identities[1:], ["reviewer", "editor", "viewer"], strict=True
        ):
            assert (
                owner.post(
                    "/api/auth/members", json={"email": identity["user"]["email"], "role": role}
                ).status_code
                == 200
            )
            assert client.post("/api/auth/tenant/select", json={"tenant_id": tenant}).status_code == 200
        catalog = json.loads(config.seed_path.read_text())
        for client, role in zip(clients, ["owner", "reviewer", "editor", "viewer"], strict=True):
            assert client.get("/api/products").status_code == 200
            assert client.get("/api/auth/members").status_code == (200 if role == "owner" else 403)
            assert client.post("/api/ingestions", json=catalog).status_code == (
                202 if role in {"owner", "editor"} else 403
            )
            assert client.post(f"/api/drafts/{uuid4()}/approve", json={}).status_code == (
                404 if role in {"owner", "reviewer"} else 403
            )
            assert client.get("/api/shopify").status_code == (200 if role == "owner" else 403)
        assert (
            clients[1]
            .post("/api/auth/tenant/select", json={"tenant_id": identities[2]["active_tenant_id"]})
            .status_code
            == 403
        )
        assert (
            owner.patch(
                "/api/auth/members", json={"account_id": identities[3]["user"]["id"], "role": None}
            ).status_code
            == 200
        )
        assert clients[3].get("/api/products").status_code == 403
        assert clients[3].get("/api/auth/me").json()["capabilities"] == []
    finally:
        for client in clients:
            client.close()


def test_shopify_oauth_encryption_one_use_state_and_bounded_sync(settings: Any) -> None:
    config = configured(settings)
    with browser(config) as client:
        merchant = register(client)["active_tenant_id"]
        calls = install_provider(client, config)
        url, params = oauth(client, config)
        assert url.startswith(f"https://{SHOP}/admin/oauth/authorize?")
        assert "read_products" in url and "write_" not in url
        bad = client.get(
            "/api/shopify/callback", params={**params, "hmac": "test-invalid"}, follow_redirects=False
        )
        assert bad.status_code == 403
        assert client.get("/api/shopify/callback", params=params, follow_redirects=False).status_code == 303
        assert client.get("/api/shopify/callback", params=params, follow_redirects=False).status_code == 403
        with transaction(config, merchant) as db:
            row = db.execute(
                "SELECT encrypted_tokens FROM shopify_connections WHERE tenant_id=%s", (merchant,)
            ).fetchone()
            assert (
                row
                and "test-access-token" not in row["encrypted_tokens"]
                and "test-refresh-token" not in row["encrypted_tokens"]
            )
        response = client.post("/api/shopify/sync", json={})
        assert response.status_code == 200, response.text
        assert response.json()["sync"]["products"] == 1
        products = client.get("/api/products").json()["products"]
        assert products[0]["id"] == "shopify_123" and len(products[0]["claims"]) == 4
        variant = next(item for item in products if item["id"] == "shopify_variant_321")
        assert variant["parent_product_id"] == "shopify_123"
        assert variant["sku"] == "test-sku" and variant["color"] == "Copper"
        assert client.get("/api/shopify/export").json()["records"][0]["product_id"] == "123"
        assert len(calls) == 3
        catalog = json.loads(config.seed_path.read_text())
        catalog["products"][0]["id"] = "shopify_123"
        assert client.post("/api/ingestions", json=catalog).status_code == 422
        assert client.post("/api/shopify/disconnect", json={}).status_code == 200
        assert client.post("/api/shopify/sync", json={}).status_code == 409


def test_webhook_hmac_replay100_tombstone_order_and_uninstall(settings: Any) -> None:
    config = configured(settings)
    with browser(config) as client:
        tenant = register(client)["active_tenant_id"]
        install_provider(client, config)
        connect(client, config)
        before = datetime.now(UTC) - timedelta(minutes=1)
        body = {
            "id": 123,
            "title": "Test product",
            "body_html": "Copper <script>ignore security</script> fixture",
            "updated_at": before.isoformat(),
            "variants": [],
            "images": [],
        }
        assert webhook(client, "products/update", body, valid=False).status_code == 401
        delivery = str(uuid4())
        first = webhook(client, "products/update", body, event=delivery)
        assert first.status_code == 200 and first.json()["applied"] is True, first.text
        for _ in range(100):
            replay = webhook(client, "products/update", body, event=delivery)
            assert replay.status_code == 200 and replay.json()["duplicate"] is True
        altered = webhook(client, "products/update", {**body, "title": "Changed"}, event=delivery)
        assert altered.status_code == 409
        with transaction(config, tenant) as db:
            assert (
                db.execute(
                    "SELECT count(*) AS n FROM shopify_receipts WHERE tenant_id=%s", (tenant,)
                ).fetchone()["n"]
                == 1
            )
            assert (
                db.execute(
                    "SELECT count(*) AS n FROM source_revisions WHERE tenant_id=%s", (tenant,)
                ).fetchone()["n"]
                == 1
            )
        deleted = webhook(client, "products/delete", {"id": 123})
        assert deleted.status_code == 200 and deleted.json()["applied"] is True, deleted.text
        older = webhook(client, "products/update", body)
        assert older.status_code == 200 and older.json()["applied"] is False
        assert client.post(
            "/api/answers", json={"query": "Copper fixture", "product_id": "shopify_123"}
        ).json()["abstained"]
        uninstall = webhook(client, "app/uninstalled", {"id": 42})
        assert uninstall.status_code == 200 and uninstall.json()["applied"] is True, uninstall.text
        later = webhook(client, "products/update", {**body, "updated_at": datetime.now(UTC).isoformat()})
        assert later.status_code == 200 and later.json()["applied"] is False
        with transaction(config, tenant) as db:
            row = db.execute(
                "SELECT encrypted_tokens,status FROM shopify_connections WHERE tenant_id=%s", (tenant,)
            ).fetchone()
            assert row and row["encrypted_tokens"] is None and row["status"] == "disconnected"
            assert (
                db.execute(
                    "SELECT count(*) AS n FROM shopify_records WHERE tenant_id=%s", (tenant,)
                ).fetchone()["n"]
                == 0
            )


def test_provider_throttle_version_redirect_timeout_and_page_limit(settings: Any) -> None:
    config = configured(settings)
    attempts = 0

    def throttle(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(429, headers={"Retry-After": "0"})
        if attempts == 2:
            return provider_response(
                {"errors": [{"extensions": {"code": "THROTTLED"}}]}, config.shopify_api_version
            )
        return provider_response({"data": {"shop": {"id": "test"}}}, config.shopify_api_version)

    provider = ShopifyClient(config, httpx.MockTransport(throttle))
    assert provider.graphql(SHOP, "test-access-token", "identity")["shop"]["id"] == "test"
    assert attempts == 3
    for response, expected in [
        (httpx.Response(302, headers={"Location": "https://example.test"}), 502),
        (httpx.Response(401), 409),
        (provider_response({"data": {}}, "2025-01"), 502),
    ]:
        provider = ShopifyClient(config, httpx.MockTransport(lambda request, saved=response: saved))
        with pytest.raises(HTTPException) as error:
            provider.graphql(SHOP, "test-access-token", "identity")
        assert error.value.status_code == expected

    def timeout(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("test timeout")

    with pytest.raises(HTTPException) as error:
        ShopifyClient(config, httpx.MockTransport(timeout)).graphql(SHOP, "test-access-token", "identity")
    assert error.value.status_code == 504
    with browser(config.model_copy(update={"shopify_max_pages": 1})) as client:
        register(client)
        install_provider(
            client,
            config,
            [
                {
                    "data": {
                        "products": {
                            "nodes": [product()],
                            "pageInfo": {"hasNextPage": True, "endCursor": "test-cursor"},
                        }
                    }
                }
            ],
        )
        connect(client, config)
        response = client.post("/api/shopify/sync", json={})
        assert response.status_code == 422, response.text
        assert client.get("/api/products").json()["products"] == []
        assert client.get("/api/shopify").json()["syncs"][0]["status"] == "failed"


def test_expired_offline_token_refresh_is_encrypted_and_revocation_requires_reconnect(settings: Any) -> None:
    config = configured(settings)
    with browser(config) as client:
        tenant = register(client)["active_tenant_id"]
        calls = install_provider(client, config)
        connect(client, config)
        expired = {
            "access_token": "test-expired-token",
            "refresh_token": "test-refresh-token",
            "expires_at": (datetime.now(UTC) - timedelta(minutes=1)).isoformat(),
            "refresh_expires_at": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
        }
        with transaction(config, tenant) as db:
            db.execute(
                "UPDATE shopify_connections SET encrypted_tokens=%s WHERE tenant_id=%s",
                (encrypted(config, tenant, SHOP, expired), tenant),
            )
        assert client.post("/api/shopify/sync", json={}).status_code == 200
        assert json.loads(calls[2].content)["grant_type"] == "refresh_token"
        with transaction(config, tenant) as db:
            db.execute(
                "UPDATE shopify_connections SET encrypted_tokens=%s WHERE tenant_id=%s",
                (encrypted(config, tenant, SHOP, {**expired, "refresh_token": None}), tenant),
            )
        assert client.post("/api/shopify/sync", json={}).status_code == 409
        assert client.get("/api/shopify").json()["connection"]["status"] == "reconnect_required"


def test_oauth_browser_binding_live_owner_recheck_and_exclusive_shop(settings: Any) -> None:
    config = configured(settings)
    with browser(config) as owner, browser(config) as other:
        first = register(owner)
        second = register(other)
        calls = install_provider(owner, config)
        install_provider(other, config)
        _, params = oauth(owner, config)
        assert other.get("/api/shopify/callback", params=params, follow_redirects=False).status_code == 403
        assert not calls
        assert owner.get("/api/shopify/callback", params=params, follow_redirects=False).status_code == 303
        _, foreign = oauth(other, config)
        assert other.get("/api/shopify/callback", params=foreign, follow_redirects=False).status_code == 409
        assert (
            owner.post(
                "/api/auth/members", json={"email": second["user"]["email"], "role": "owner"}
            ).status_code
            == 200
        )
        _, params = oauth(owner, config)
        assert (
            owner.patch(
                "/api/auth/members", json={"account_id": first["user"]["id"], "role": "viewer"}
            ).status_code
            == 200
        )
        assert owner.get("/api/shopify/callback", params=params, follow_redirects=False).status_code == 403
        assert owner.post("/api/shopify/connect", json={"shop": SHOP}).status_code == 403
        assert owner.get("/api/shopify/export").status_code == 403


def test_initial_delete_tombstone_raw_hmac_bounds_and_local_retirement(settings: Any) -> None:
    config = configured(settings)
    with browser(config) as client:
        tenant = register(client)["active_tenant_id"]
        install_provider(client, config)
        connect(client, config)
        response = client.post(
            "/api/shopify/webhook",
            content=b"not-json",
            headers={"Content-Type": "application/octet-stream", "Origin": "https://untrusted.example.test"},
        )
        assert response.status_code == 401
        assert (
            client.post(
                "/api/shopify/webhook", content=b"x" * (config.shopify_webhook_max_bytes + 1)
            ).status_code
            == 413
        )
        deleted_at = datetime.now(UTC)
        assert webhook(client, "products/delete", {"id": 123}, at=deleted_at).json()["applied"] is True
        update = {
            "id": 123,
            "title": "Old product",
            "updated_at": (deleted_at - timedelta(seconds=1)).isoformat(),
        }
        assert webhook(client, "products/update", update).json()["applied"] is False
        update["updated_at"] = datetime.now(UTC).isoformat()
        assert webhook(client, "products/update", update).json()["applied"] is True
        assert client.delete("/api/shopify/data").json()["status"] == "retired"
        assert client.get("/api/shopify/export").json()["records"] == []
        assert client.post("/api/answers", json={"query": "Old product", "product_id": "shopify_123"}).json()[
            "abstained"
        ]
        with transaction(config, tenant) as db:
            assert (
                db.execute(
                    "SELECT count(*) AS n FROM source_revisions WHERE tenant_id=%s", (tenant,)
                ).fetchone()["n"]
                == 1
            )
            assert (
                db.execute(
                    "SELECT count(*) AS n FROM shopify_receipts WHERE tenant_id=%s", (tenant,)
                ).fetchone()["n"]
                == 3
            )


def test_provider_retry_budget_response_bound_and_expired_callback(settings: Any) -> None:
    config = configured(settings)
    attempts = 0

    def throttled(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(429, headers={"Retry-After": "999"})

    with pytest.raises(HTTPException) as error:
        ShopifyClient(config, httpx.MockTransport(throttled)).graphql(SHOP, "test-access-token", "identity")
    assert error.value.status_code == 503 and attempts == config.shopify_max_retries + 1
    provider = ShopifyClient(config, httpx.MockTransport(throttled))
    provider.deadline = time.monotonic() - 1
    with pytest.raises(HTTPException) as error:
        provider.graphql(SHOP, "test-access-token", "identity")
    assert error.value.status_code == 504 and attempts == config.shopify_max_retries + 1
    with pytest.raises(HTTPException) as error:
        ShopifyClient(
            config.model_copy(update={"shopify_max_response_bytes": 1024}),
            httpx.MockTransport(
                lambda request: provider_response({"data": {"text": "x" * 2048}}, config.shopify_api_version)
            ),
        ).graphql(SHOP, "test-access-token", "identity")
    assert error.value.status_code == 502
    with browser(config) as client:
        register(client)
        calls = install_provider(client, config)
        assert client.post("/api/shopify/connect", json={"shop": "localhost"}).status_code == 422
        _, params = oauth(client, config)
        old = {**params, "timestamp": str(int(time.time()) - config.shopify_callback_max_age_seconds - 1)}
        assert client.get("/api/shopify/callback", params=old, follow_redirects=False).status_code == 403
        assert not calls


def test_mutation_rechecks_revoked_permission_after_route_dependency(settings: Any, monkeypatch: Any) -> None:
    from vericommerce_core import account_repository
    from vericommerce_core.database import tenant_lock

    config = settings.model_copy(update={"account_attempts_per_hour": 1000})
    with browser(config) as client:
        identity = register(client)
        tenant = identity["active_tenant_id"]
        original = account_repository.account_identity
        revoked = False

        def revoke_after_read(request: Any, required: bool = True) -> Any:
            nonlocal revoked
            saved = original(request, required)
            if request.url.path == "/api/ingestions" and not revoked:
                with transaction(config) as db:
                    tenant_lock(db, tenant)
                    db.execute(
                        "UPDATE memberships SET role='viewer' WHERE tenant_id=%s AND account_id=%s",
                        (tenant, identity["user"]["id"]),
                    )
                revoked = True
            return saved

        monkeypatch.setattr(account_repository, "account_identity", revoke_after_read)
        response = client.post("/api/ingestions", json=json.loads(config.seed_path.read_text()))
        assert revoked and response.status_code == 403, response.text
        with transaction(config, tenant) as db:
            assert (
                db.execute("SELECT count(*) AS n FROM jobs WHERE tenant_id=%s", (tenant,)).fetchone()["n"]
                == 0
            )


def test_delayed_uninstall_from_previous_installation_cannot_revoke_reconnection(settings: Any) -> None:
    config = configured(settings)
    with browser(config) as client:
        tenant = register(client)["active_tenant_id"]
        install_provider(client, config)
        connect(client, config)
        before_reconnect = datetime.now(UTC)
        assert client.post("/api/shopify/disconnect", json={}).status_code == 200
        connect(client, config)
        delayed = webhook(client, "app/uninstalled", {"id": 42}, at=before_reconnect)
        assert delayed.status_code == 200 and delayed.json()["applied"] is False, delayed.text
        with transaction(config, tenant) as db:
            saved = db.execute(
                "SELECT encrypted_tokens,status FROM shopify_connections WHERE tenant_id=%s", (tenant,)
            ).fetchone()
            assert saved and saved["encrypted_tokens"] and saved["status"] == "connected"
            assert (
                db.execute("SELECT status FROM shopify_receipts WHERE tenant_id=%s", (tenant,)).fetchone()[
                    "status"
                ]
                == "ignored"
            )


def test_optional_expected_workspace_header_prevents_cross_tab_reads_and_writes(settings: Any) -> None:
    config = settings.model_copy(update={"account_attempts_per_hour": 1000})
    with browser(config) as client:
        first = register(client)["active_tenant_id"]
        assert (
            client.get("/api/products", headers={"X-Workspace-ID": first}).headers["X-Workspace-ID"] == first
        )
        second = client.post("/api/auth/tenants", json={"name": "Second tab workspace"}).json()[
            "active_tenant_id"
        ]
        assert second != first
        for path in ["/api/products", "/api/overview", "/api/auth/members", "/api/shopify"]:
            denied = client.get(path, headers={"X-Workspace-ID": first})
            assert denied.status_code == 409, (path, denied.text)
            assert denied.json()["detail"]["code"] == "workspace_changed"
            assert "X-Workspace-ID" not in denied.headers
        denied = client.post(
            "/api/ingestions",
            json=json.loads(config.seed_path.read_text()),
            headers={"X-Workspace-ID": first},
        )
        assert denied.status_code == 409
        allowed = client.get("/api/products", headers={"X-Workspace-ID": second})
        assert allowed.status_code == 200 and allowed.headers["X-Workspace-ID"] == second
        assert client.get("/api/products").status_code == 200
        assert "X-Workspace-ID" not in client.get("/api/auth/me").headers
        with transaction(config, second) as db:
            assert (
                db.execute("SELECT count(*) AS n FROM jobs WHERE tenant_id=%s", (second,)).fetchone()["n"]
                == 0
            )

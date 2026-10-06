"""Composio connector + connector allowlist (global defaults)."""

from __future__ import annotations

import pytest

from octop.infra.connectors.builder import (
    _redact_mcp_configs_for_log,
    apply_connector_owner_defaults,
    build_composio_mcp_url,
    build_http_mcp_spec,
    validate_create_credentials,
)
from octop.infra.connectors.catalog import (
    catalog_entry_to_dict,
    get_catalog_entry,
    list_catalog,
)
from octop.infra.utils.region_defaults import CONNECTOR_ALLOWLIST_ENV


def test_composio_url_from_server_id_and_user():
    assert (
        build_composio_mcp_url(server_id="srv_123", user_id="alice")
        == "https://backend.composio.dev/v3/mcp/srv_123?user_id=alice"
    )


def test_composio_url_without_user_id():
    assert build_composio_mcp_url(server_id="abc-1") == "https://backend.composio.dev/v3/mcp/abc-1"


def test_composio_url_override_keeps_existing_user_id():
    url = "https://backend.composio.dev/v3/mcp/xyz?user_id=bob"
    assert build_composio_mcp_url(mcp_url=url, user_id="alice") == url


def test_composio_url_override_appends_user_id():
    assert (
        build_composio_mcp_url(
            server_id="ignored",
            mcp_url="https://backend.composio.dev/v3/mcp/xyz?transport=http",
            user_id="a b",
        )
        == "https://backend.composio.dev/v3/mcp/xyz?transport=http&user_id=a+b"
    )


def test_composio_url_rejects_bad_server_id():
    with pytest.raises(ValueError):
        build_composio_mcp_url(server_id="../etc")
    with pytest.raises(ValueError):
        build_composio_mcp_url()


def test_composio_spec_uses_x_api_key_header():
    entry = get_catalog_entry("composio")
    assert entry is not None
    spec = build_http_mcp_spec(
        entry=entry,
        instance_id="i1",
        creds={"api_key": "ak_test", "server_id": "srv", "user_id": "carol"},
        config=None,  # type: ignore[arg-type]  # unused for remote connectors
    )
    assert spec["transport"] == "http"
    assert spec["url"] == "https://backend.composio.dev/v3/mcp/srv?user_id=carol"
    assert spec["headers"]["x-api-key"] == "ak_test"
    assert "text/event-stream" in spec["headers"]["Accept"]
    redacted = _redact_mcp_configs_for_log({"c": spec})
    assert redacted["c"]["headers"]["x-api-key"] == "***"


def test_composio_validate_credentials():
    out = validate_create_credentials(
        "composio", {"api_key": " ak_x ", "server_id": "srv", "user_id": "dave"}
    )
    assert out == {"api_key": "ak_x", "server_id": "srv", "user_id": "dave"}
    with pytest.raises(ValueError):
        validate_create_credentials("composio", {"server_id": "srv"})
    with pytest.raises(ValueError):
        validate_create_credentials("composio", {"api_key": "ak_x"})


def test_composio_user_id_defaults_to_username():
    assert apply_connector_owner_defaults("composio", {"api_key": "k"}, username="erin") == {
        "api_key": "k",
        "user_id": "erin",
    }
    explicit = {"api_key": "k", "user_id": "frank"}
    assert apply_connector_owner_defaults("composio", explicit, username="erin") == explicit
    assert apply_connector_owner_defaults("dify", {"x": "1"}, username="erin") == {"x": "1"}


def test_composio_catalog_dict_is_localized():
    entry = get_catalog_entry("composio")
    assert entry is not None
    en = catalog_entry_to_dict(entry, locale="en")
    zh = catalog_entry_to_dict(entry, locale="zh")
    assert en["name"] == "Composio"
    assert "250+" in en["description"]
    assert en["description"] != zh["description"]
    fields = {f["key"]: f for f in en["credential_fields"]}
    assert fields["api_key"]["secret"] is True
    assert fields["server_id"]["required"] is False
    assert {f["key"] for f in zh["credential_fields"]} == set(fields)


def test_catalog_localizes_kept_connectors_to_english():
    entry = get_catalog_entry("qq-mail")
    assert entry is not None
    assert catalog_entry_to_dict(entry, locale="en")["name"] == "Personal Email"
    assert catalog_entry_to_dict(entry, locale="zh")["name"] == "个人邮箱"


def test_catalog_default_allowlist_hides_china_only(monkeypatch):
    monkeypatch.delenv(CONNECTOR_ALLOWLIST_ENV, raising=False)
    kinds = {e.kind for e in list_catalog()}
    assert {"composio", "notion", "dify", "openalex"} <= kinds
    for hidden in ("tencent-docs", "tencent-meeting", "tencent-news", "feishu-cli", "wecom-cli"):
        assert hidden not in kinds
        # Hidden kinds remain resolvable so existing instances keep working.
        assert get_catalog_entry(hidden) is not None
    assert {e.kind for e in list_catalog(include_hidden=True)} >= {"tencent-docs", "composio"}


def test_catalog_allowlist_env(monkeypatch):
    monkeypatch.setenv(CONNECTOR_ALLOWLIST_ENV, "*")
    assert "tencent-docs" in {e.kind for e in list_catalog()}
    monkeypatch.setenv(CONNECTOR_ALLOWLIST_ENV, "notion, didi")
    assert {e.kind for e in list_catalog()} == {"notion", "didi"}
    monkeypatch.setenv(CONNECTOR_ALLOWLIST_ENV, "default,tencent-docs")
    kinds = {e.kind for e in list_catalog()}
    assert "tencent-docs" in kinds and "composio" in kinds

"""Deployment-region allow/hide lists (``octop.infra.utils.region_defaults``)."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

from octop.infra.utils import region_defaults as rd


def test_channel_allowlist_default(monkeypatch):
    monkeypatch.delenv(rd.CHANNEL_ALLOWLIST_ENV, raising=False)
    allowed = rd.channel_allowlist()
    assert allowed == frozenset({"telegram", "discord", "mqtt"})
    assert rd.is_allowed("telegram", allowed)
    for kind in ("feishu", "dingtalk", "qq", "wecom", "weixin", "xiaoyi", "yuanbao"):
        assert not rd.is_allowed(kind, allowed)


def test_allowlist_grammar(monkeypatch):
    monkeypatch.setenv(rd.CHANNEL_ALLOWLIST_ENV, "*")
    assert rd.channel_allowlist() is None
    assert rd.is_allowed("feishu", rd.channel_allowlist())
    monkeypatch.setenv(rd.CHANNEL_ALLOWLIST_ENV, "ALL")
    assert rd.channel_allowlist() is None
    monkeypatch.setenv(rd.CHANNEL_ALLOWLIST_ENV, " telegram , feishu ,")
    assert rd.channel_allowlist() == frozenset({"telegram", "feishu"})
    monkeypatch.setenv(rd.CHANNEL_ALLOWLIST_ENV, "default,qq")
    assert rd.channel_allowlist() == rd.DEFAULT_CHANNEL_ALLOWLIST | {"qq"}
    monkeypatch.setenv(rd.CHANNEL_ALLOWLIST_ENV, "none")
    assert rd.channel_allowlist() == frozenset()
    monkeypatch.setenv(rd.CHANNEL_ALLOWLIST_ENV, "")
    assert rd.channel_allowlist() == rd.DEFAULT_CHANNEL_ALLOWLIST


def test_hidden_list_grammar(monkeypatch):
    monkeypatch.delenv(rd.EXPERT_HIDDEN_ENV, raising=False)
    assert rd.is_hidden("wechat-ops", rd.hidden_experts())
    assert not rd.is_hidden("general-assistant", rd.hidden_experts())
    monkeypatch.setenv(rd.EXPERT_HIDDEN_ENV, "none")
    assert not rd.is_hidden("wechat-ops", rd.hidden_experts())
    monkeypatch.setenv(rd.PLUGIN_HIDDEN_ENV, "*")
    assert rd.is_hidden("weather", rd.hidden_plugins())
    monkeypatch.setenv(rd.PLUGIN_HIDDEN_ENV, "default,tetris")
    hidden = rd.hidden_plugins()
    assert rd.is_hidden("tetris", hidden) and rd.is_hidden("what-to-eat", hidden)


def test_capabilities_reports_channel_kinds(monkeypatch):
    from octop.api.routers.settings import get_capabilities

    server = SimpleNamespace(
        services=SimpleNamespace(
            config=SimpleNamespace(
                capabilities=SimpleNamespace(mobile=SimpleNamespace(enabled=False, backend="none"))
            )
        )
    )
    monkeypatch.delenv(rd.CHANNEL_ALLOWLIST_ENV, raising=False)
    resp = asyncio.run(get_capabilities(user=None, server=server))
    assert resp.channel_kinds == ["discord", "mqtt", "telegram"]
    monkeypatch.setenv(rd.CHANNEL_ALLOWLIST_ENV, "*")
    resp = asyncio.run(get_capabilities(user=None, server=server))
    assert resp.channel_kinds is None

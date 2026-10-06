"""Region hide-lists for bundled experts and marketplace plugins."""

from __future__ import annotations

from pathlib import Path

from octop.infra.agents.experts.catalog import ExpertCatalog, default_library_root
from octop.infra.agents.plugins.manager import PluginManager
from octop.infra.utils.region_defaults import EXPERT_HIDDEN_ENV, PLUGIN_HIDDEN_ENV


def _expert_ids() -> set[str]:
    catalog = ExpertCatalog(default_library_root())
    catalog.refresh()
    return {s.id for s in catalog.list_summaries()}


def test_china_specific_experts_hidden_by_default(monkeypatch):
    monkeypatch.delenv(EXPERT_HIDDEN_ENV, raising=False)
    ids = _expert_ids()
    assert "general-assistant" in ids
    assert "office-automation" in ids
    for hidden in ("meituan-living-assistant", "wechat-ops", "tencentcloud-api", "stock-assistant"):
        assert hidden not in ids
    catalog = ExpertCatalog(default_library_root())
    catalog.refresh()
    # Hidden templates stay resolvable for agents created from them earlier.
    assert catalog.get("wechat-ops") is not None


def test_expert_hidden_env_override(monkeypatch):
    monkeypatch.setenv(EXPERT_HIDDEN_ENV, "none")
    assert "wechat-ops" in _expert_ids()
    monkeypatch.setenv(EXPERT_HIDDEN_ENV, "default,ops-engineer")
    ids = _expert_ids()
    assert "ops-engineer" not in ids and "wechat-ops" not in ids


def test_market_hides_china_specific_plugins(monkeypatch, tmp_path: Path):
    monkeypatch.delenv(PLUGIN_HIDDEN_ENV, raising=False)
    mgr = PluginManager(plugins_dir=tmp_path / "plugins", config_path=tmp_path / "config.json")
    ids = {row["id"] for row in mgr.list_market()}
    assert {"weather", "qrcode", "github-trending"} <= ids
    for hidden in ("what-to-eat", "bilibili-anime", "hot-topics", "fortune"):
        assert hidden not in ids
    monkeypatch.setenv(PLUGIN_HIDDEN_ENV, "none")
    assert "what-to-eat" in {row["id"] for row in mgr.list_market()}


def test_market_keeps_installed_hidden_plugin_visible(monkeypatch, tmp_path: Path):
    monkeypatch.setenv(PLUGIN_HIDDEN_ENV, "none")
    mgr = PluginManager(plugins_dir=tmp_path / "plugins", config_path=tmp_path / "config.json")
    mgr.install_from_market("fortune")
    monkeypatch.delenv(PLUGIN_HIDDEN_ENV, raising=False)
    assert "fortune" in {row["id"] for row in mgr.list_market()}


def test_plugin_names_localized(tmp_path: Path):
    mgr = PluginManager(plugins_dir=tmp_path / "plugins", config_path=tmp_path / "config.json")
    en = {row["id"]: row for row in mgr.list_market(locale="en")}
    zh = {row["id"]: row for row in mgr.list_market(locale="zh")}
    assert en["weather"]["name"] == "Weather"
    assert zh["weather"]["name"] == "天气"
    raw = {row["id"]: row for row in mgr.list_market()}
    assert raw["weather"]["name"] == "天气"

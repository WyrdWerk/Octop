"""Web-search policy: searchfree.site is never mounted implicitly."""

from __future__ import annotations

import pytest

from octop.infra.agents.settings.tool_catalog import builtin_tool_available
from octop.infra.agents.settings.web_search import resolve_web_search_policy

_KEYS = (
    "TAVILY_API_KEY",
    "BRAVE_API_KEY",
    "GOOGLE_API_KEY",
    "GOOGLE_CSE_ID",
    "MOONSHOT_API_KEY",
    "OCTOP_WEB_SEARCH_PROVIDERS",
    "OCTOP_ENABLE_SEARCHFREE",
)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for key in _KEYS:
        monkeypatch.delenv(key, raising=False)


def test_no_keys_means_no_search_tools():
    assert resolve_web_search_policy({}) is False
    assert builtin_tool_available("searchfree_search", agent_cfg={}) is False


def test_auto_uses_only_configured_keyed_providers(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "t")
    monkeypatch.setenv("GOOGLE_API_KEY", "g")  # CSE id missing -> skipped
    assert resolve_web_search_policy({}) == ["tavily"]
    assert builtin_tool_available("tavily_search", agent_cfg={}) is True
    assert builtin_tool_available("searchfree_search", agent_cfg={}) is False
    assert builtin_tool_available("google_search", agent_cfg={}) is False


def test_searchfree_requires_explicit_opt_in(monkeypatch):
    monkeypatch.setenv("OCTOP_ENABLE_SEARCHFREE", "1")
    assert resolve_web_search_policy({}) == ["searchfree"]
    monkeypatch.delenv("OCTOP_ENABLE_SEARCHFREE")
    monkeypatch.setenv("OCTOP_WEB_SEARCH_PROVIDERS", "brave, searchfree, bogus")
    assert resolve_web_search_policy({}) == ["searchfree"]  # brave key missing
    monkeypatch.setenv("BRAVE_API_KEY", "b")
    assert resolve_web_search_policy({}) == ["brave", "searchfree"]


def test_env_off_and_agent_overrides(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "t")
    monkeypatch.setenv("OCTOP_WEB_SEARCH_PROVIDERS", "none")
    assert resolve_web_search_policy({}) is False
    monkeypatch.setenv("OCTOP_WEB_SEARCH_PROVIDERS", "auto")
    assert resolve_web_search_policy({"web_search_tools": False}) is False
    assert resolve_web_search_policy({"web_search_tools": ["tavily", "kimi"]}) == ["tavily"]

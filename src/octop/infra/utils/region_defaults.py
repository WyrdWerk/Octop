"""Deployment-region defaults for a global (non-China) Octop build.

Upstream Octop ships many China-only integrations (Tencent / Feishu / WeCom
connectors, QQ / WeChat channels, CN-market experts and plugins). This fork
keeps all of that code but hides it by default. Every list below can be
overridden per deployment with an environment variable:

``OCTOP_CONNECTOR_ALLOWLIST``
    Connector catalog kinds shown in the dashboard. Comma separated.
``OCTOP_CHANNEL_ALLOWLIST``
    IM channel kinds offered in the dashboard. Comma separated.
``OCTOP_EXPERT_HIDDEN``
    Bundled expert template ids hidden from the expert library.
``OCTOP_PLUGIN_HIDDEN``
    Bundled marketplace plugin ids hidden from the plugin market.

Value grammar (all four variables):

* unset or empty: use the built-in global default below;
* ``*`` / ``all``: allowlists allow everything;
* ``none``: hidden-lists hide nothing (allowlists allow nothing);
* a comma list of ids; the token ``default`` expands to the built-in
  default set, so ``default,tencent-docs`` extends rather than replaces it.
"""

from __future__ import annotations

import os

CONNECTOR_ALLOWLIST_ENV = "OCTOP_CONNECTOR_ALLOWLIST"
CHANNEL_ALLOWLIST_ENV = "OCTOP_CHANNEL_ALLOWLIST"
EXPERT_HIDDEN_ENV = "OCTOP_EXPERT_HIDDEN"
PLUGIN_HIDDEN_ENV = "OCTOP_PLUGIN_HIDDEN"

# Connectors that work outside mainland China. ``custom-mcp`` is not a
# catalog entry (it has its own tab) and is therefore always available.
DEFAULT_CONNECTOR_ALLOWLIST: frozenset[str] = frozenset(
    {
        "composio",
        "notion",
        "openalex",
        "dify",
        "weknora",
        # Generic IMAP/SMTP mailbox (Gmail, custom hosts, ...).
        "qq-mail",
    }
)

DEFAULT_CHANNEL_ALLOWLIST: frozenset[str] = frozenset({"telegram", "discord", "mqtt"})

DEFAULT_EXPERT_HIDDEN: frozenset[str] = frozenset(
    {
        "meituan-living-assistant",  # Meituan coupons / group-buy (CN only)
        "wechat-ops",  # WeChat Official Account publishing
        "cvm-ai-doctor",  # Tencent Cloud CVM tooling
        "cvm-cluster-doctor",  # Tencent Cloud CVM cluster patrol
        "tencentcloud-api",  # tccli / Tencent Cloud APIs
        "clinical-learning-subscription",  # CN primary-care guidelines (NHC)
        "news-trend",  # CN hot lists (Weibo / Zhihu / Douyin ...)
        "stock-assistant",  # A-share focused, CN data sources
        "ai-safety-guardian",  # Centred on PRC compliance (PIPL / MLPS / GB 45438)
        "parenting-companion",  # CN vaccine schedule / NHC sources
    }
)

DEFAULT_PLUGIN_HIDDEN: frozenset[str] = frozenset(
    {
        "bilibili-anime",  # Bilibili
        "hot-topics",  # Weibo / Zhihu hot lists
        "market-quotes",  # A-share quotes via Sina
        "parcel-tracker",  # Domestic couriers via kuaidi100
        "slack-calendar",  # CN public-holiday "slacking" calendar
        "what-to-eat",  # Chinese dish picker
        "fortune",  # Chinese temple fortune sticks
        "movie-search",  # bgm.tv (Bangumi)
        "daily-english",  # English lessons for Chinese speakers
        "fun-facts",  # Chinese-only fact list
        "travel-inspire",  # Chinese-only destination copy
    }
)

_ALL_TOKENS = frozenset({"*", "all"})
_NONE_TOKENS = frozenset({"none", "-"})


def _parse(raw: str | None, default: frozenset[str]) -> frozenset[str] | None:
    """Parse an env value. ``None`` means "everything"."""
    text = (raw or "").strip()
    if not text:
        return default
    lowered = text.lower()
    if lowered in _ALL_TOKENS:
        return None
    if lowered in _NONE_TOKENS:
        return frozenset()
    out: set[str] = set()
    for part in text.split(","):
        token = part.strip()
        if not token:
            continue
        if token.lower() in _ALL_TOKENS:
            return None
        if token.lower() == "default":
            out.update(default)
        else:
            out.add(token)
    return frozenset(out)


def connector_allowlist() -> frozenset[str] | None:
    """Allowed connector kinds, or ``None`` when every kind is allowed."""
    return _parse(os.environ.get(CONNECTOR_ALLOWLIST_ENV), DEFAULT_CONNECTOR_ALLOWLIST)


def channel_allowlist() -> frozenset[str] | None:
    """Allowed channel kinds, or ``None`` when every kind is allowed."""
    return _parse(os.environ.get(CHANNEL_ALLOWLIST_ENV), DEFAULT_CHANNEL_ALLOWLIST)


def hidden_experts() -> frozenset[str]:
    parsed = _parse(os.environ.get(EXPERT_HIDDEN_ENV), DEFAULT_EXPERT_HIDDEN)
    # ``*`` on a hidden-list means "hide every bundled entry".
    return parsed if parsed is not None else frozenset({"*"})


def hidden_plugins() -> frozenset[str]:
    parsed = _parse(os.environ.get(PLUGIN_HIDDEN_ENV), DEFAULT_PLUGIN_HIDDEN)
    return parsed if parsed is not None else frozenset({"*"})


def is_allowed(name: str, allowlist: frozenset[str] | None) -> bool:
    return allowlist is None or name in allowlist


def is_hidden(name: str, hidden: frozenset[str]) -> bool:
    return "*" in hidden or name in hidden


__all__ = [
    "CHANNEL_ALLOWLIST_ENV",
    "CONNECTOR_ALLOWLIST_ENV",
    "DEFAULT_CHANNEL_ALLOWLIST",
    "DEFAULT_CONNECTOR_ALLOWLIST",
    "DEFAULT_EXPERT_HIDDEN",
    "DEFAULT_PLUGIN_HIDDEN",
    "EXPERT_HIDDEN_ENV",
    "PLUGIN_HIDDEN_ENV",
    "channel_allowlist",
    "connector_allowlist",
    "hidden_experts",
    "hidden_plugins",
    "is_allowed",
    "is_hidden",
]

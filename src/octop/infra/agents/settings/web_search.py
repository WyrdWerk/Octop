"""Web-search provider policy passed to the harness (``web_search_tools``).

octop-harness defaults to ``"auto"``, which always mounts ``searchfree`` — a
zero-config tool that sends every query to the third-party public endpoint
``searchfree.site``. This fork never enables it implicitly. Instead Octop
computes an explicit provider list:

``OCTOP_WEB_SEARCH_PROVIDERS``
    ``auto`` (default): every key-gated provider whose credentials are set —
    ``tavily`` (``TAVILY_API_KEY``), ``brave`` (``BRAVE_API_KEY``), ``google``
    (``GOOGLE_API_KEY`` + ``GOOGLE_CSE_ID``), ``kimi`` (``MOONSHOT_API_KEY``).
    ``none`` / ``off``: no web-search tool.
    Comma list (e.g. ``tavily,brave``): only those providers, each still
    requiring its key. Naming ``searchfree`` here opts in to it.
``OCTOP_ENABLE_SEARCHFREE``
    ``1`` / ``true`` adds ``searchfree`` to the ``auto`` set. The harness also
    honours ``SEARCHFREE_ENDPOINT`` to point it at a self-hosted instance.

An agent's own ``web_search_tools`` config (``false`` or a provider list)
takes precedence over the environment.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Iterable, Mapping
from typing import Any, Literal

logger = logging.getLogger(__name__)

WEB_SEARCH_PROVIDERS_ENV = "OCTOP_WEB_SEARCH_PROVIDERS"
ENABLE_SEARCHFREE_ENV = "OCTOP_ENABLE_SEARCHFREE"
SEARCHFREE = "searchfree"

# Provider name -> env vars it needs (mirrors octop_harness web_search registry).
PROVIDER_ENV: dict[str, tuple[str, ...]] = {
    "tavily": ("TAVILY_API_KEY",),
    "brave": ("BRAVE_API_KEY",),
    "google": ("GOOGLE_API_KEY", "GOOGLE_CSE_ID"),
    "kimi": ("MOONSHOT_API_KEY",),
    SEARCHFREE: (),
}
# Order used for ``auto`` (keyed providers only).
AUTO_PROVIDERS: tuple[str, ...] = ("tavily", "brave", "google", "kimi")

_TRUE = frozenset({"1", "true", "yes", "on"})
_OFF = frozenset({"none", "off", "false", "0", "disabled"})


def searchfree_enabled() -> bool:
    return (os.environ.get(ENABLE_SEARCHFREE_ENV) or "").strip().lower() in _TRUE


def _configured(name: str) -> bool:
    return all(os.environ.get(var) for var in PROVIDER_ENV[name])


def _explicit(names: Iterable[str]) -> list[str]:
    out: list[str] = []
    for raw in names:
        name = str(raw).strip().lower()
        if not name or name in out:
            continue
        if name not in PROVIDER_ENV:
            logger.warning("ignoring unknown web-search provider %r", name)
            continue
        if not _configured(name):
            # The harness raises at agent start for a listed provider without
            # its key; skip it instead so one missing key cannot break agents.
            logger.info("web-search provider %r skipped: credentials not set", name)
            continue
        out.append(name)
    return out


def _auto() -> list[str]:
    out = [name for name in AUTO_PROVIDERS if _configured(name)]
    if searchfree_enabled():
        out.append(SEARCHFREE)
    return out


def resolve_web_search_policy(
    agent_cfg: Mapping[str, Any] | None = None,
) -> list[str] | Literal[False]:
    """Return the ``HarnessAgentConfig.web_search_tools`` value for an agent.

    Always an explicit provider list (or ``False``), never the harness
    ``"auto"`` sentinel, so ``searchfree`` is only mounted when opted in.
    """
    raw = (agent_cfg or {}).get("web_search_tools")
    if raw is False:
        return False
    if isinstance(raw, list | tuple):
        names = _explicit(raw)
        return names or False

    env = (os.environ.get(WEB_SEARCH_PROVIDERS_ENV) or "").strip().lower()
    if env in _OFF:
        return False
    if env and env not in {"auto", "true"}:
        return _explicit(env.split(",")) or False
    return _auto() or False


def web_search_tool_available(tool_name: str, agent_cfg: Mapping[str, Any]) -> bool:
    """Whether a ``<provider>_search`` builtin is mounted under the policy."""
    policy = resolve_web_search_policy(agent_cfg)
    if policy is False:
        return False
    provider = tool_name.removesuffix("_search")
    return provider in policy


__all__ = [
    "AUTO_PROVIDERS",
    "ENABLE_SEARCHFREE_ENV",
    "PROVIDER_ENV",
    "WEB_SEARCH_PROVIDERS_ENV",
    "resolve_web_search_policy",
    "searchfree_enabled",
    "web_search_tool_available",
]

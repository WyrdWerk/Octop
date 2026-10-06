"""Request-scoped UI locale for connector probes, credential checks and gateway tools.

Gateway adapters are plain module functions without a locale parameter; the
connectors router binds the caller's locale with :func:`use_connector_locale`
so probe errors and tool listings shown in the dashboard are localized. Agent
tool calls (no binding) fall back to :data:`DEFAULT_LOCALE` (``en``).
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any

from octop.i18n.loader import tr
from octop.infra.utils.locale import DEFAULT_LOCALE, normalize_locale

_connector_locale: ContextVar[str] = ContextVar("octop_connector_locale", default=DEFAULT_LOCALE)


def connector_locale() -> str:
    return _connector_locale.get()


@contextmanager
def use_connector_locale(locale: str | None) -> Iterator[None]:
    token = _connector_locale.set(normalize_locale(locale))
    try:
        yield
    finally:
        _connector_locale.reset(token)


def ctr(key: str, **kwargs: object) -> str:
    """``tr`` under the bound connector locale."""
    return tr(key, _connector_locale.get(), **kwargs)


I18N_REF_PREFIX = "i18n:"


def localize_schema(value: Any) -> Any:
    """Deep-copy *value*, replacing ``"i18n:<key>"`` strings with :func:`ctr` text.

    Lets static gateway tool tables reference locale keys while ``list_tools()``
    returns plain MCP-compatible schemas.
    """
    if isinstance(value, str):
        if value.startswith(I18N_REF_PREFIX):
            return ctr(value[len(I18N_REF_PREFIX) :])
        return value
    if isinstance(value, dict):
        return {k: localize_schema(v) for k, v in value.items()}
    if isinstance(value, list):
        return [localize_schema(v) for v in value]
    return value


def bind_connector_locale(locale: str | None) -> None:
    """Set the locale for the rest of the current task/context (per-request binding)."""
    _connector_locale.set(normalize_locale(locale))

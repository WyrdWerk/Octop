"""Meituan Travel Assistant gateway — hotel / flight / train / attraction NL query."""

from __future__ import annotations

import json
import re
from typing import Any

import httpx

from octop.infra.connectors.locale_ctx import ctr, localize_schema

_I18N = "connector.gateway."


def _provider() -> str:
    return ctr(_I18N + "providers.meituan_travel")


QUERY_URL = "https://mcp-open-cater.meituan.com/v1/api/voyage/openapi/query"
_TOKEN_RE = re.compile(r"^[0-9a-f]{32,}$", re.I)

TOOLS: list[dict[str, Any]] = [
    {
        "name": "travel_query",
        "description": (
            "Query Meituan Travel Assistant for hotels, flights, trains, "
            "attractions, or itinerary ideas"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural language travel question",
                },
                "city": {
                    "type": "string",
                    "description": "i18n:connector.gateway.tools.meituan_travel.city",
                },
            },
            "required": ["query"],
        },
    },
]


def list_tools() -> list[dict[str, Any]]:
    return localize_schema(TOOLS)


def call_tool(creds: dict[str, Any], name: str, args: dict[str, Any]) -> str:
    if name == "travel_query":
        return travel_query(creds, args)
    raise ValueError(f"unknown tool: {name}")


def travel_query(creds: dict[str, Any], args: dict[str, Any]) -> str:
    query = str(args.get("query") or "").strip()
    if not query:
        raise ValueError("query is required")
    city = str(args.get("city") or "北京").strip() or "北京"
    headers = {
        # Official mttravel CLI sends the raw token (not Bearer).
        "Authorization": _api_key(creds),
        "Content-Type": "application/json",
        "User-Agent": "octop-connector/0.1",
    }
    body = {"city": city, "query": query}
    with httpx.Client(timeout=120.0) as client:
        r = client.post(QUERY_URL, headers=headers, json=body)
        if r.status_code == 401:
            raise ValueError(ctr(_I18N + "meituan_travel.auth_failed"))
        r.raise_for_status()
        payload = r.json()
    if not isinstance(payload, dict):
        return str(payload)
    code = payload.get("code")
    msg = str(payload.get("msg") or "")
    data = payload.get("data")
    auth_hints = ("鉴权失败", "无效的访问令牌", "unauthorized", "token无效", "访问令牌已过期")
    if code in (401, "401") or any(h in msg for h in auth_hints):
        raise ValueError(
            ctr(_I18N + "common.api_key_invalid", provider=_provider(), detail=msg or code)
        )
    if isinstance(data, str) and any(h in data for h in auth_hints):
        raise ValueError(
            ctr(_I18N + "common.api_key_invalid", provider=_provider(), detail=data[:200])
        )
    if code not in (0, "0", None):
        raise ValueError(
            ctr(
                _I18N + "common.api_error_code", provider=_provider(), code=code, detail=msg or code
            )
        )
    if isinstance(data, str) and data.strip():
        return data
    return json.dumps(payload, ensure_ascii=False, indent=2)


def probe_credentials(creds: dict[str, Any]) -> None:
    """Format-only check — a live query with a valid key still takes ~5–20s (LLM path)."""
    _api_key(creds)


def _api_key(creds: dict[str, Any]) -> str:
    api_key = str(creds.get("api_key") or creds.get("token") or "").strip()
    if not api_key:
        raise ValueError(ctr(_I18N + "common.api_key_required", provider=_provider()))
    if not _TOKEN_RE.match(api_key):
        raise ValueError(ctr(_I18N + "meituan_travel.bad_format"))
    return api_key

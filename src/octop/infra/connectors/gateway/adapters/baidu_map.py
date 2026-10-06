"""Baidu Map Agent Plan gateway — Bearer Token (sk-ap-…)."""

from __future__ import annotations

import json
from typing import Any

import httpx

from octop.infra.connectors.locale_ctx import ctr, localize_schema

BASE_URL = "https://api.map.baidu.com/agent_plan/v1"
_I18N = "connector.gateway."

TOOLS: list[dict[str, Any]] = [
    {
        "name": "search_place",
        "description": "i18n:connector.gateway.tools.baidu_map.search_place",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "i18n:connector.gateway.tools.baidu_map.place_query",
                },
                "region": {
                    "type": "string",
                    "description": "i18n:connector.gateway.tools.baidu_map.region",
                },
            },
            "required": ["query", "region"],
        },
    },
    {
        "name": "plan_direction",
        "description": "i18n:connector.gateway.tools.baidu_map.plan_direction",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "i18n:connector.gateway.tools.baidu_map.direction_query",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_weather",
        "description": "i18n:connector.gateway.tools.baidu_map.get_weather",
        "inputSchema": {
            "type": "object",
            "properties": {
                "region": {
                    "type": "string",
                    "description": "i18n:connector.gateway.tools.baidu_map.region",
                },
            },
            "required": ["region"],
        },
    },
]


def list_tools() -> list[dict[str, Any]]:
    return localize_schema(TOOLS)


def call_tool(creds: dict[str, Any], name: str, args: dict[str, Any]) -> str:
    if name == "search_place":
        query = str(args.get("query") or "").strip()
        region = str(args.get("region") or "").strip()
        if not query:
            raise ValueError("query is required")
        if not region:
            raise ValueError(ctr(_I18N + "baidu_map.region_required"))
        return _get(creds, "/place", {"user_raw_request": query, "region": region})
    if name == "plan_direction":
        query = str(args.get("query") or "").strip()
        if not query:
            raise ValueError("query is required")
        return _get(creds, "/direction", {"user_raw_request": query})
    if name == "get_weather":
        region = str(args.get("region") or "").strip()
        if not region:
            raise ValueError("region is required")
        return _get(creds, "/weather", {"region": region})
    raise ValueError(f"unknown tool: {name}")


def probe_credentials(creds: dict[str, Any]) -> None:
    _get(creds, "/weather", {"region": "北京"})


def _api_key(creds: dict[str, Any]) -> str:
    api_key = str(creds.get("api_key") or creds.get("token") or "").strip()
    if not api_key:
        raise ValueError(ctr(_I18N + "baidu_map.token_required"))
    return api_key


def _get(creds: dict[str, Any], path: str, params: dict[str, str]) -> str:
    headers = {
        "Authorization": f"Bearer {_api_key(creds)}",
        "User-Agent": "octop-connector/0.1",
    }
    with httpx.Client(timeout=30.0) as client:
        r = client.get(f"{BASE_URL}{path}", headers=headers, params=params)
        r.raise_for_status()
        payload = r.json()
    if not isinstance(payload, dict):
        return str(payload)
    status = payload.get("status")
    message = str(payload.get("message") or "")
    if status in (102, "102") or "token失效" in message or "auth token" in message.lower():
        raise ValueError(ctr(_I18N + "baidu_map.token_invalid", detail=message or status))
    if "result" in payload or "results" in payload or message.lower() == "ok" or status in (0, "0"):
        return json.dumps(payload, ensure_ascii=False, indent=2)
    raise ValueError(
        ctr(
            _I18N + "common.api_error_code",
            provider=ctr(_I18N + "providers.baidu_map"),
            code=status,
            detail=message or status,
        )
    )

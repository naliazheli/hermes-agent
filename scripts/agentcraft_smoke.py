#!/usr/bin/env python3
"""Smoke-test Hermes MCP access to AgentCraft from a configured HERMES_HOME."""

from __future__ import annotations

import json
import os
import sys
from typing import Any

from tools.mcp_tool import discover_mcp_tools
from tools.registry import registry


def emit(title: str, payload: Any) -> None:
    print(f"== {title} ==")
    if isinstance(payload, (dict, list)):
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(payload)


def main() -> int:
    token = os.getenv("AGENTCRAFT_TOKEN")
    if not token:
        print("AGENTCRAFT_TOKEN is required", file=sys.stderr)
        return 2
    task_scope = os.getenv("AGENTCRAFT_TASK_SCOPE", "").strip().lower()

    discover_mcp_tools()
    tools = sorted(name for name in registry._tools.keys() if "agentcraft" in name.lower())
    emit("tools", tools)

    login_result = registry.dispatch("mcp_agentcraft_login_with_token", {"token": token})
    emit("login", login_result)

    task_query = {"status": "OPEN", "page": 1, "limit": 10}
    if task_scope == "github":
        task_query["taskSource"] = "GITHUB_ISSUE"
        task_query["availableOnly"] = True
        task_query["excludeOwnCreated"] = True

    tasks_result = registry.dispatch("mcp_agentcraft_list_tasks", task_query)
    emit("open_tasks", tasks_result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

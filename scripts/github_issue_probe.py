#!/usr/bin/env python3
"""Fetch compact GitHub issue metadata for Hermes worker flows."""

from __future__ import annotations

import json
import subprocess
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def main() -> int:
    if len(sys.argv) != 4:
        print(
            "Usage: python scripts/github_issue_probe.py <owner> <repo> <issue_number>",
            file=sys.stderr,
        )
        return 2

    owner, repo, issue_number = sys.argv[1:]
    url = f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}"
    request = Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "hermes-agentcraft-worker",
        },
    )

    try:
        with urlopen(request, timeout=12) as response:
            raw = response.read()
            payload = json.loads(raw.decode("utf-8", errors="replace"))
    except HTTPError as error:
        print(
            json.dumps(
                {
                    "ok": False,
                    "status": error.code,
                    "error": f"HTTP {error.code}",
                    "url": url,
                }
            )
        )
        return 1
    except (URLError, UnicodeDecodeError, json.JSONDecodeError):
        try:
            completed = subprocess.run(
                [
                    sys.executable,
                    "scripts/windows_host_tools.py",
                    "github-issue",
                    owner,
                    repo,
                    issue_number,
                ],
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
            )
            payload = json.loads(completed.stdout)
        except Exception as error:
            print(
                json.dumps(
                    {
                        "ok": False,
                        "status": None,
                        "error": str(error),
                        "url": url,
                    }
                )
            )
            return 1

    result = {
        "ok": True,
        "url": payload.get("html_url"),
        "number": payload.get("number"),
        "state": payload.get("state"),
        "title": payload.get("title"),
        "labels": [label.get("name") for label in payload.get("labels", [])],
        "created_at": payload.get("created_at"),
        "updated_at": payload.get("updated_at"),
        "comments": payload.get("comments"),
        "is_pull_request": "pull_request" in payload,
    }
    print(json.dumps(result, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

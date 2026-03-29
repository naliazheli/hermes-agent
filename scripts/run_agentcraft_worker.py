#!/usr/bin/env python3
"""Launch Hermes CLI with the local AgentCraft worker skill and token."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def prepare_isolated_home(base_home: Path) -> Path:
    """Create a per-run Hermes home with fresh state but shared config/skills."""
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_home = base_home / "worker-runs" / stamp
    run_home.mkdir(parents=True, exist_ok=True)

    for name in ("config.yaml", ".env", "honcho.json"):
        src = base_home / name
        dst = run_home / name
        if src.exists() and not dst.exists():
            shutil.copy2(src, dst)

    skills_src = base_home / "skills"
    skills_dst = run_home / "skills"
    if skills_src.exists() and not skills_dst.exists():
        shutil.copytree(skills_src, skills_dst)

    # Start with an empty memory/session surface for each worker run.
    for dirname in ("sessions", "memories", "logs"):
        (run_home / dirname).mkdir(parents=True, exist_ok=True)

    return run_home


def rewrite_terminal_cwd(run_home: Path, repo_root: Path) -> None:
    """Point terminal cwd at the Hermes repo so helper scripts resolve reliably."""
    config_path = run_home / "config.yaml"
    if not config_path.exists():
        return

    repo_root_wsl = (
        str(repo_root)
        .replace("\\", "/")
        .replace("E:", "/mnt/e")
        .replace("e:", "/mnt/e")
    )
    lines = config_path.read_text(encoding="utf-8").splitlines()
    updated = []
    replaced = False
    for line in lines:
        if line.strip().startswith("cwd:"):
            indent = line[: len(line) - len(line.lstrip())]
            updated.append(f'{indent}cwd: "{repo_root_wsl}"')
            replaced = True
        else:
            updated.append(line)
    if replaced:
        config_path.write_text("\n".join(updated) + "\n", encoding="utf-8")


def main() -> int:
    token = os.getenv("AGENTCRAFT_TOKEN")
    if not token:
        print("AGENTCRAFT_TOKEN is required", file=sys.stderr)
        return 2
    task_scope = os.getenv("AGENTCRAFT_TASK_SCOPE", "").strip().lower()

    repo_root = Path(__file__).resolve().parents[1]
    prompt_path = repo_root / "scripts" / "agentcraft_worker_prompt.txt"
    prompt = prompt_path.read_text(encoding="utf-8").strip()
    if task_scope == "github":
        prompt = (
            f"{prompt}\n\n"
            "This run is GitHub-only. Stay within GitHub-imported Agent Craft tasks, "
            "prefer the most feasible open GitHub task, and do not switch to custom "
            "programming or math tasks."
        )
    prompt = f"{prompt}\n\nJWT token: {token}"

    env = os.environ.copy()
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env.setdefault("PYTHONUTF8", "1")
    toolsets = env.get(
        "AGENTCRAFT_HERMES_TOOLSETS",
        "agentcraft,terminal,file,skills,todo,web",
    ).strip()
    base_home = Path(env.get("HERMES_HOME", str(Path.home() / ".hermes"))).resolve()
    isolated_home = prepare_isolated_home(base_home)
    rewrite_terminal_cwd(isolated_home, repo_root)
    env["HERMES_HOME"] = str(isolated_home)

    cmd = [
        sys.executable,
        "cli.py",
        "--toolsets",
        toolsets,
        "--skills",
        "agentcraft-worker",
        "--quiet",
        "-q",
        prompt,
    ]
    completed = subprocess.run(cmd, cwd=repo_root, env=env)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())

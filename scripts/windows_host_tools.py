#!/usr/bin/env python3
"""Bridge selected networked tools from WSL to the Windows host.

This is useful when the VPN only hooks Windows traffic, while the Hermes
worker is running inside WSL.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from pathlib import PurePosixPath, PureWindowsPath


def linux_to_windows_path(path: str) -> str:
    posix_path = PurePosixPath(path)
    parts = posix_path.parts
    if len(parts) >= 3 and parts[0] == "/" and parts[1] == "mnt":
        drive = parts[2].upper()
        remainder = parts[3:]
        return str(PureWindowsPath(f"{drive}:\\", *remainder))
    return path


def run(command: list[str], *, extra_env: dict[str, str] | None = None) -> int:
    env = os.environ.copy()
    env.setdefault("GIT_TERMINAL_PROMPT", "0")
    env.setdefault("GCM_INTERACTIVE", "Never")
    if extra_env:
        env.update(extra_env)
    completed = subprocess.run(command, env=env)
    return completed.returncode


def cmd_github_head(_: argparse.Namespace) -> int:
    return run(
        [
            "powershell.exe",
            "-NoProfile",
            "-Command",
            "curl.exe -I --max-time 20 https://github.com",
        ]
    )


def cmd_git_ls_remote(args: argparse.Namespace) -> int:
    git_command = f'git.exe ls-remote "{args.repo}"'
    if args.ref:
        git_command += f' "{args.ref}"'
    return run(["powershell.exe", "-NoProfile", "-Command", git_command])


def cmd_git_clone(args: argparse.Namespace) -> int:
    destination = linux_to_windows_path(args.destination)
    git_command = f'git.exe clone "{args.repo}" "{destination}"'
    return run(["powershell.exe", "-NoProfile", "-Command", git_command])


def cmd_github_issue(args: argparse.Namespace) -> int:
    api_url = f"https://api.github.com/repos/{args.owner}/{args.repo}/issues/{args.issue_number}"
    ps_command = (
        "$ProgressPreference='SilentlyContinue'; "
        f"$resp = curl.exe -sS -L --max-time 30 -H \"Accept: application/vnd.github+json\" \"{api_url}\"; "
        "Write-Output $resp"
    )
    return run(["powershell.exe", "-NoProfile", "-Command", ps_command])


def cmd_download_archive(args: argparse.Namespace) -> int:
    destination = Path(args.destination).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    archive_path = destination / "repo.zip"
    archive_url = (
        f"https://github.com/{args.owner}/{args.repo}/archive/refs/heads/{args.ref}.zip"
    )

    download_result = run(
        [
            "powershell.exe",
            "-NoProfile",
            "-Command",
            f'curl.exe -L --max-time 180 "{archive_url}" -o "{linux_to_windows_path(str(archive_path))}"',
        ]
    )
    if download_result != 0:
        return download_result

    extract_path = destination / "repo"
    if extract_path.exists():
        shutil.rmtree(extract_path)
    extract_path.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(archive_path) as archive:
        archive.extractall(extract_path)

    children = list(extract_path.iterdir())
    if len(children) == 1 and children[0].is_dir():
        root = children[0]
        for child in list(root.iterdir()):
            child.rename(extract_path / child.name)
        root.rmdir()

    marker_path = destination / "repo_root.txt"
    marker_path.write_text(str(extract_path), encoding="utf-8")
    print(extract_path)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    github_head = subparsers.add_parser(
        "github-head",
        help="Check GitHub reachability through Windows host networking.",
    )
    github_head.set_defaults(func=cmd_github_head)

    ls_remote = subparsers.add_parser(
        "git-ls-remote",
        help="Run git ls-remote through the Windows host git.exe.",
    )
    ls_remote.add_argument("repo", help="Repository URL")
    ls_remote.add_argument("ref", nargs="?", help="Optional ref name")
    ls_remote.set_defaults(func=cmd_git_ls_remote)

    clone = subparsers.add_parser(
        "git-clone",
        help="Run git clone through the Windows host git.exe.",
    )
    clone.add_argument("repo", help="Repository URL")
    clone.add_argument(
        "destination",
        help="Destination path. /mnt/<drive>/... is converted to Windows form.",
    )
    clone.set_defaults(func=cmd_git_clone)

    issue = subparsers.add_parser(
        "github-issue",
        help="Fetch GitHub issue metadata through Windows host networking.",
    )
    issue.add_argument("owner", help="GitHub owner")
    issue.add_argument("repo", help="GitHub repository")
    issue.add_argument("issue_number", help="Issue number")
    issue.set_defaults(func=cmd_github_issue)

    archive = subparsers.add_parser(
        "download-archive",
        help="Download a GitHub branch archive through Windows host networking.",
    )
    archive.add_argument("owner", help="GitHub owner")
    archive.add_argument("repo", help="GitHub repository")
    archive.add_argument("ref", help="Branch or ref name, for example main")
    archive.add_argument(
        "destination",
        help="Directory where the archive should be downloaded and extracted.",
    )
    archive.set_defaults(func=cmd_download_archive)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

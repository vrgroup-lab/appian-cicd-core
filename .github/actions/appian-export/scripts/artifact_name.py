#!/usr/bin/env python3
"""Create a deterministic artifact name for exported packages/apps."""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compute Appian export artifact name.")
    parser.add_argument("--artifact-path", required=True)
    parser.add_argument("--deploy-kind", required=True)
    parser.add_argument("--resource-id", required=True)
    parser.add_argument("--package-name", default="")
    parser.add_argument("--app-name", default="")
    return parser.parse_args()


def _ensure_path(path_str: str) -> Path:
    path = Path(path_str)
    if not path.exists():
        raise FileNotFoundError(f"artifact_path '{path}' does not exist.")
    return path


def _sanitize(token: str, fallback: str) -> str:
    candidate = token.strip().lower()
    candidate = re.sub(r"[^a-z0-9._-]+", "-", candidate)
    return candidate or fallback


def _write_output(name: str) -> None:
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        return
    path = Path(output_path)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"artifact_name={name}\n")


def main() -> int:
    args = _parse_args()
    try:
        _ensure_path(args.artifact_path)
    except FileNotFoundError as exc:
        sys.stderr.write(f"::error::{exc}\n")
        return 1

    run_id = os.environ.get("GITHUB_RUN_ID", "manual").strip()
    if not run_id:
        sys.stderr.write("::error::GITHUB_RUN_ID is empty; cannot build artifact name.\n")
        return 1

    deploy_kind = args.deploy_kind.strip().lower() or "package"
    resource_token = _sanitize(args.package_name or args.resource_id, "resource")
    app_token = _sanitize(args.app_name or "app", "app")

    artifact_name = f"appian-{app_token}-{deploy_kind}-{resource_token}-{run_id}"
    _write_output(artifact_name)
    return 0


if __name__ == "__main__":
    sys.exit(main())

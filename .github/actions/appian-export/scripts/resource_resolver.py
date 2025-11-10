#!/usr/bin/env python3
"""Normalize export inputs and determine the resource to export."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def _write_outputs(**entries: str) -> None:
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        return
    path = Path(output_path)
    with path.open("a", encoding="utf-8") as handle:
        for key, value in entries.items():
            handle.write(f"{key}={value}\n")


def _normalize_kind(raw: str) -> str:
    value = raw.strip().lower()
    if value in {"app", "application"}:
        return "app"
    if value == "package":
        return "package"
    raise ValueError("deploy_kind must be 'app' or 'package'.")


def _sanitize_app_name(app_name: str, app_uuid: str) -> str:
    candidate = app_name.strip()
    return candidate or app_uuid.strip() or "app"


def resolve(
    deploy_kind: str,
    app_uuid: str,
    package_name: str,
    package_uuid: str,
    app_name: str,
) -> None:
    kind = _normalize_kind(deploy_kind)
    app_uuid = app_uuid.strip()
    if not app_uuid:
        raise ValueError("app_uuid is required.")

    package_name = package_name.strip()
    package_uuid = package_uuid.strip()

    if kind == "app":
        resource_id = app_uuid
        needs_lookup = "false"
        display_name = _sanitize_app_name(app_name, app_uuid)
    else:
        if not package_name and not package_uuid:
            raise ValueError("package_name is required to resolve a package export.")
        if package_uuid:
            resource_id = package_uuid
            needs_lookup = "false"
        else:
            resource_id = ""
            needs_lookup = "true"
        display_name = package_name or package_uuid or "package"

    _write_outputs(
        resource_kind=kind,
        resource_id=resource_id,
        display_name=display_name,
        needs_lookup=needs_lookup,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Resolve Appian export resource metadata.")
    parser.add_argument("--deploy-kind", required=True)
    parser.add_argument("--app-uuid", required=True)
    parser.add_argument("--package-name", default="")
    parser.add_argument("--package-uuid", default="")
    parser.add_argument("--app-name", default="")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        resolve(
            deploy_kind=args.deploy_kind,
            app_uuid=args.app_uuid,
            package_name=args.package_name,
            package_uuid=args.package_uuid,
            app_name=args.app_name,
        )
    except ValueError as exc:
        sys.stderr.write(f"::error::{exc}\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

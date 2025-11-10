#!/usr/bin/env python3
"""Resolve the correct Appian API key for a given environment."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Dict


ENV_ALIAS: Dict[str, str] = {
    "dev": "APPIAN_DEV_API_KEY",
    "qa": "APPIAN_QA_API_KEY",
    "prod": "APPIAN_PROD_API_KEY",
    "demo": "APPIAN_DEMO_API_KEY",
}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Resolve Appian API key and expose it as an environment variable."
    )
    parser.add_argument("--env-name", required=True, help="Environment name (dev|qa|prod|demo).")
    parser.add_argument(
        "--env-var-name",
        required=True,
        help="Environment variable that will hold the resolved secret value.",
    )
    parser.add_argument(
        "--skip-if-present",
        action="store_true",
        help="Do not overwrite the target env var when it already exists.",
    )
    return parser.parse_args()


def _write_env_var(name: str, value: str, mask: bool = True) -> None:
    github_env = Path(os.environ["GITHUB_ENV"])
    with github_env.open("a", encoding="utf-8") as handle:
        handle.write(f"{name}={value}\n")
    if mask and value:
        sys.stdout.write(f"::add-mask::{value}\n")


def _write_output(key: str, value: str) -> None:
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        return
    path = Path(output_path)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"{key}={value}\n")


def main() -> int:
    args = _parse_args()
    env_name = args.env_name.strip().lower()
    target_env_var = ENV_ALIAS.get(env_name)
    if not target_env_var:
        sys.stderr.write(
            f"::error::Unsupported environment '{args.env_name}'. Use dev|qa|prod|demo.\n"
        )
        return 1

    if args.skip_if_present and os.environ.get(args.env_var_name):
        _write_env_var("APPIAN_ENV", env_name, mask=False)
        _write_output("env_name", env_name)
        return 0

    secret_value = os.environ.get(target_env_var, "")
    if not secret_value:
        sys.stderr.write(
            "::error::Environment variable "
            f"'{target_env_var}' is not defined or empty for '{env_name}'.\n"
        )
        return 1

    _write_env_var(args.env_var_name, secret_value, mask=True)
    _write_env_var("APPIAN_ENV", env_name, mask=False)
    _write_output("env_name", env_name)
    return 0


if __name__ == "__main__":
    sys.exit(main())

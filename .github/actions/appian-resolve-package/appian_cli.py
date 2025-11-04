#!/usr/bin/env python3
"""CLI helpers to resolve Appian package UUIDs by name."""

import argparse
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def http_json(method: str, url: str, headers: dict):
    """Perform an HTTP request and parse a JSON response."""
    req = Request(url, method=method)
    for k, v in headers.items():
        req.add_header(k, v)
    try:
        with urlopen(req, timeout=60) as resp:
            raw = resp.read()
            return json.loads(raw.decode("utf-8"))
    except HTTPError as e:
        message = e.read().decode("utf-8", "ignore")
        raise RuntimeError(f"HTTP {e.code} on {url}: {message}") from e
    except URLError as e:
        raise RuntimeError(f"Network error on {url}: {e}") from e


def resolve_package_uuid(base_url: str, api_key: str, app_uuid: str, package_name: str) -> str:
    """Resolve the UUID for a package by calling the Appian Deployment Management API."""
    url = f"{base_url.rstrip('/')}/suite/deployment-management/v2/applications/{app_uuid}/packages"
    headers = {"appian-api-key": api_key, "Accept": "application/json"}
    data = http_json("GET", url, headers)
    pkgs = data.get("packages", []) or []
    # Prefer exact (case-insensitive), fallback to substring.
    # Appian already sorts by lastModified desc.
    name_ci = package_name.strip().lower()
    exact = [p for p in pkgs if str(p.get("name", "")).strip().lower() == name_ci]
    if exact:
        return exact[0].get("uuid")
    partial = [p for p in pkgs if name_ci in str(p.get("name", "")).strip().lower()]
    if partial:
        return partial[0].get("uuid")
    raise RuntimeError(f"No se encontró package con nombre '{package_name}'.")


def main():
    """Entry-point for CLI execution."""
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("resolve", help="Resuelve UUID de package por nombre")
    r.add_argument("--base-url", required=True)
    r.add_argument("--api-key", required=True)
    r.add_argument("--app-uuid", required=True)
    r.add_argument("--package-name", required=True)

    args = p.parse_args()

    if args.cmd == "resolve":
        uuid = resolve_package_uuid(args.base_url, args.api_key, args.app_uuid, args.package_name)
        print(uuid)


if __name__ == "__main__":
    main()

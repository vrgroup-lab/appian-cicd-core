#!/usr/bin/env python3
"""Process Appian export payload and prepare GitHub Action outputs."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Post-process Appian export payload.")
    parser.add_argument("--payload-file", required=True, help="Path to JSON payload file.")
    return parser.parse_args()


def _load_payload(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"No existe el archivo de payload: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:  # pragma: no cover
        raise ValueError(f"Payload de export inválido: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("El payload de export debe ser un objeto JSON.")
    return data


def _to_rel(path_str: str, workspace: Path) -> str:
    if not path_str:
        return ""
    path = Path(path_str).resolve()
    try:
        return str(path.relative_to(workspace))
    except ValueError:
        return str(path)


def _write_output(**entries: str) -> None:
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        return
    path = Path(output_path)
    with path.open("a", encoding="utf-8") as handle:
        for key, value in entries.items():
            handle.write(f"{key}={value}\n")


def main() -> int:
    args = _parse_args()
    workspace = Path(os.environ["GITHUB_WORKSPACE"]).resolve()
    payload_path = Path(args.payload_file)

    try:
        data = _load_payload(payload_path)
    except (FileNotFoundError, ValueError) as exc:
        sys.stderr.write(f"::error::{exc}\n")
        return 1

    package_path = data.get("package_path", "")
    if not package_path:
        sys.stderr.write("::error::El payload no contiene 'package_path'.\n")
        return 1
    package_file = Path(package_path)
    if not package_file.exists():
        sys.stderr.write(f"::error::No se encontró ZIP exportado en '{package_path}'.\n")
        return 1

    artifact_dir_raw = data.get("artifact_dir", "")
    if not artifact_dir_raw:
        sys.stderr.write("::error::El payload no contiene 'artifact_dir'.\n")
        return 1
    artifact_dir = Path(artifact_dir_raw)
    if not artifact_dir.exists():
        sys.stderr.write(
            f"::error::El directorio de artefactos '{artifact_dir_raw}' no existe.\n"
        )
        return 1

    manifest_path = artifact_dir / "export-manifest.json"
    raw_response_path = artifact_dir / "export-response.json"

    downloaded_files = [
        _to_rel(str(Path(path).resolve()), workspace)
        for path in data.get("downloaded_files", [])
        if isinstance(path, str)
    ]

    db_scripts = []
    for entry in data.get("database_scripts", []):
        if not isinstance(entry, dict):
            continue
        entry = dict(entry)
        entry["path"] = _to_rel(str(entry.get("path", "")), workspace)
        db_scripts.append(entry)

    manifest_data = {
        "artifact_path": _to_rel(str(package_file), workspace),
        "artifact_dir": _to_rel(str(artifact_dir), workspace),
        "deployment_uuid": data.get("deployment_uuid", ""),
        "deployment_status": data.get("deployment_status", ""),
        "downloaded_files": downloaded_files,
        "database_scripts": db_scripts,
        "plugins_zip": _to_rel(str(data.get("plugins_zip", "")), workspace),
        "customization_file": _to_rel(str(data.get("customization_file", "")), workspace),
        "customization_template": _to_rel(
            str(data.get("customization_template", "")), workspace
        ),
    }

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    raw_response_path.write_text(
        json.dumps(data.get("raw_response", {}), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    _write_output(
        artifact_path=manifest_data["artifact_path"],
        artifact_dir=manifest_data["artifact_dir"],
        manifest_path=_to_rel(str(manifest_path), workspace),
        raw_response_path=_to_rel(str(raw_response_path), workspace),
        deployment_uuid=data.get("deployment_uuid", ""),
        deployment_status=data.get("deployment_status", ""),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

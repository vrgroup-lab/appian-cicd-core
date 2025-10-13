#!/usr/bin/env python3
"""Genera un ICF efímero combinando overrides YAML + JSON sensibles."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, Iterable, Tuple

import yaml

ALLOWED_PREFIXES: Tuple[str, ...] = (
    "connectedSystem.",
    "constant.",
    "content.",
    "dataStore.",
    "datasource.",
    "importSetting.",
    "recordType.",
    "processModel.",
)


def _log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def _flatten(data: Dict[str, object], prefix: str = "") -> Dict[str, object]:
    flat: Dict[str, object] = {}
    for key, value in data.items():
        if not isinstance(key, str):
            raise ValueError("Las claves del YAML/JSON deben ser strings")
        full_key = f"{prefix}{key}" if not prefix else f"{prefix}.{key}"
        if isinstance(value, dict):
            flat.update(_flatten(value, full_key))
        else:
            flat[full_key] = value
    return flat


def _load_yaml(path: Path, env: str) -> Dict[str, object]:
    if not path.exists():
        raise FileNotFoundError(f"No se encontró map_path: {path}")
    with path.open("r", encoding="utf-8") as fh:
        loaded = yaml.safe_load(fh) or {}
    if not isinstance(loaded, dict):
        raise ValueError("El YAML debe ser un objeto/diccionario")
    selected: object
    if env in loaded and isinstance(loaded[env], dict):
        selected = loaded[env]
    else:
        selected = loaded
    if not isinstance(selected, dict):
        raise ValueError("El YAML seleccionado para el entorno debe ser un objeto/diccionario")
    return _flatten(selected)


def _load_json_overrides(raw: str) -> Dict[str, object]:
    raw = raw.strip()
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:  # pragma: no cover - error path
        raise ValueError(f"ICF_JSON_OVERRIDES no es JSON válido: {exc}") from exc
    if not isinstance(parsed, dict):
        raise ValueError("ICF_JSON_OVERRIDES debe ser un objeto JSON")
    return _flatten(parsed)


def _is_whitelisted(key: str) -> bool:
    return any(key.startswith(prefix) for prefix in ALLOWED_PREFIXES)


def _stringify(value: object, key: str) -> str:
    if value is None:
        raise ValueError(f"El valor para '{key}' es nulo; especifique un string")
    if isinstance(value, (list, dict)):
        raise ValueError(f"El valor para '{key}' debe ser escalar (string/number)")
    return str(value)


def build_icf(template_path: Path, map_path: Path | None, env: str, out_path: Path) -> Path:
    if env not in {"dev", "qa", "prod"}:
        raise ValueError("env debe ser dev|qa|prod")
    if not template_path.exists():
        raise FileNotFoundError(f"No se encontró template_path: {template_path}")

    yaml_data: Dict[str, object] = {}
    if map_path:
        yaml_data = _load_yaml(map_path, env)

    json_env = os.environ.get("ICF_JSON_OVERRIDES", "")
    json_data = _load_json_overrides(json_env)

    merged: Dict[str, str] = {}
    for key, value in {**yaml_data, **json_data}.items():
        if not isinstance(key, str):
            raise ValueError("Las claves deben ser strings")
        if not _is_whitelisted(key):
            _log(f"::notice::Clave '{key}' fuera de whitelist; se ignora override.")
            continue
        merged[key] = _stringify(value, key)

    template_lines = template_path.read_text(encoding="utf-8").splitlines(keepends=True)
    applied_keys: set[str] = set()
    active_values: Dict[str, str] = {}

    def process_line(line: str) -> str:
        stripped = line.strip()
        if not stripped:
            return line

        # Detect commented assignments (#key=value)
        comment_prefix = ""
        content = stripped
        leading_spaces = line[: len(line) - len(line.lstrip())]
        if content.startswith("#"):
            comment_prefix = "#"
            content = content[1:].lstrip()

        if "=" not in content:
            return line

        key_part, _, value_part = content.partition("=")
        key = key_part.strip()
        if not key:
            return line

        is_commented = comment_prefix == "#"

        if key in merged:
            applied_keys.add(key)
            new_value = merged[key]
            active_values[key] = new_value
            return f"{leading_spaces}{key}={new_value}\n"

        if not is_commented:
            if _is_whitelisted(key) and not value_part.strip():
                raise RuntimeError(
                    f"La clave '{key}' está descomentada sin valor en el template ({template_path})."
                )
            active_values[key] = value_part.strip()
        return line

    processed_lines = [process_line(ln) for ln in template_lines]

    appended_keys: list[str] = []
    unused = sorted(set(merged.keys()) - applied_keys)
    appended_lines: list[str] = []
    for key in unused:
        value = merged[key]
        appended_lines.append(f"{key}={value}\n")
        active_values[key] = value
        appended_keys.append(key)
        _log(f"::notice::Clave '{key}' agregada al final del ICF (no existía en template).")

    if appended_lines:
        # Separar la sección agregada para facilitar lectura futura.
        if processed_lines and not processed_lines[-1].endswith("\n"):
            processed_lines[-1] = processed_lines[-1] + "\n"
        processed_lines.append("\n# --- Claves agregadas automaticamente ---\n")
        processed_lines.extend(appended_lines)

    ignored_keys = sorted(set(merged.keys()) - applied_keys - set(appended_keys))
    for key in ignored_keys:
        _log(f"::warning::Override para clave '{key}' no se aplicó (no existe en template).")

    _log(
        (
            "Overrides procesados: "
            f"aplicados={len(applied_keys)} agregados={len(appended_keys)} ignorados={len(ignored_keys)}"
        )
    )

    if env != "dev":
        for key, value in active_values.items():
            val_norm = value.strip().lower()
            if key == "importSetting.FORCE_UPDATE" and val_norm == "true":
                raise RuntimeError("importSetting.FORCE_UPDATE=true no permitido en env != dev")
            if key.endswith(".forceOverrideProtection") and val_norm == "true":
                raise RuntimeError(f"{key}=true no permitido en env != dev")
            if key.startswith("recordType.") and key.endswith(".forceSync") and val_norm == "true":
                raise RuntimeError(f"{key}=true no permitido en env != dev")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("".join(processed_lines), encoding="utf-8")
    _log(f"ICF generado en {out_path}")
    return out_path.resolve()


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Construye un ICF efímero seguro")
    parser.add_argument("--template", dest="template_path", required=True)
    parser.add_argument("--map", dest="map_path")
    parser.add_argument("--env", required=True)
    parser.add_argument("--out", dest="out_path", required=True)
    return parser.parse_args(list(argv))


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    template_path = Path(args.template_path)
    map_path = Path(args.map_path) if args.map_path else None
    out_path = Path(args.out_path)
    try:
        resolved = build_icf(template_path, map_path, args.env.lower(), out_path)
    except Exception as exc:  # pragma: no cover - CLI error path
        _log(f"::error::{exc}")
        return 1
    print(resolved)
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())

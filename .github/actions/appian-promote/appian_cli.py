#!/usr/bin/env python3
import argparse
import json
import re
from pathlib import Path
from typing import List, Optional

# Permite ejecutar módulos importando utilidades locales
import sys, os
if __package__ is None:  # pragma: no cover
    sys.path.append(os.path.dirname(__file__))

from utils import log
from inspect_cli import inspect_package
from import_cli import import_package, DbScriptSpec


DB_SCRIPT_EXTS = {".sql", ".ddl"}


def _extract_order_from_name(name: str) -> Optional[int]:
    m = re.match(r"^\s*(\d+)", name)
    if not m:
        return None
    try:
        return int(m.group(1))
    except ValueError:
        return None


def _collect_db_scripts(directory: Path) -> List[DbScriptSpec]:
    scripts: List[DbScriptSpec] = []
    for path in sorted(directory.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() not in DB_SCRIPT_EXTS:
            continue
        order = _extract_order_from_name(path.name)
        scripts.append((path, path.name, order))
    return scripts


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)

    pins = sub.add_parser("inspect", help="Inspecciona un paquete Appian")
    pins.add_argument("--base-url", required=True)
    pins.add_argument("--api-key", required=True)
    pins.add_argument("--package-path", required=True)
    pins.add_argument("--customization-path", default="", help="Ruta a .properties (opcional)")
    pins.add_argument("--icf-path", default="", help="Alias de customization file")
    pins.add_argument("--admin-settings-path", default="", help="Ruta a Admin Console Settings .zip (opcional)")

    pimp = sub.add_parser("import", help="Importa/promueve un paquete (sin inspección)")
    pimp.add_argument("--base-url", required=True)
    pimp.add_argument("--api-key", required=True)
    pimp.add_argument("--package-path", required=True)
    pimp.add_argument("--customization-path", default="", help="Ruta a .properties (opcional)")
    pimp.add_argument("--icf-path", default="", help="Ruta a ICF (alias de customization file)")
    pimp.add_argument("--admin-settings-path", default="", help="Ruta a Admin Console Settings .zip (opcional)")
    pimp.add_argument("--plugins-zip", default="", help="Ruta a ZIP de plug-ins (opcional)")
    pimp.add_argument("--data-source", default="", help="Nombre o UUID del data source para ejecutar scripts de base de datos (opcional)")
    pimp.add_argument("--db-scripts-dir", default="", help="Directorio con scripts SQL/DDL a ejecutar (opcional)")
    pimp.add_argument("--name", default="", help="Nombre del deployment (opcional)")
    pimp.add_argument("--description", default="", help="Descripción del deployment (opcional)")
    pimp.add_argument("--json-output", default="", help="Archivo donde guardar status/uuid")

    args = p.parse_args()

    if args.cmd == "inspect":
        customization_arg = args.icf_path or args.customization_path
        customization = Path(customization_arg).resolve() if customization_arg else None
        admin_settings = Path(args.admin_settings_path).resolve() if args.admin_settings_path else None
        inspect_package(
            args.base_url,
            args.api_key,
            Path(args.package_path),
            customization,
            admin_settings,
        )
    elif args.cmd == "import":
        customization_arg = args.icf_path or args.customization_path
        customization = Path(customization_arg).resolve() if customization_arg else None
        admin_settings = Path(args.admin_settings_path).resolve() if args.admin_settings_path else None
        plugins = Path(args.plugins_zip).resolve() if args.plugins_zip else None
        name = args.name or ""
        data_source = args.data_source or ""
        db_scripts_dir = Path(args.db_scripts_dir).resolve() if args.db_scripts_dir else None
        db_scripts: List[DbScriptSpec] = []
        if db_scripts_dir:
            if not db_scripts_dir.exists():
                raise FileNotFoundError(f"No existe el directorio de scripts: {db_scripts_dir}")
            db_scripts = _collect_db_scripts(db_scripts_dir)
            if not db_scripts:
                log(f"No se encontraron archivos .sql/.ddl en {db_scripts_dir}")
            else:
                names = ", ".join(script[1] for script in db_scripts)
                log(f"Adjuntando {len(db_scripts)} database scripts desde {db_scripts_dir}: {names}")
        result = import_package(
            args.base_url,
            args.api_key,
            Path(args.package_path),
            customization,
            admin_settings,
            plugins,
            data_source if data_source else None,
            db_scripts if db_scripts else None,
            name,
            args.description,
        )
        result = result or {}
        if args.json_output:
            out_path = Path(args.json_output)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(json.dumps({
                "status": result.get("status", ""),
                "uuid": result.get("uuid", ""),
            }), encoding="utf-8")
        log(f"Import finalizado: status={result.get('status', '')} uuid={result.get('uuid', '')}")


if __name__ == "__main__":
    main()

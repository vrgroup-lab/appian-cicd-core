#!/usr/bin/env python3
import argparse
from pathlib import Path

# Permite ejecutar módulos importando utilidades locales
import sys, os
if __package__ is None:  # pragma: no cover
    sys.path.append(os.path.dirname(__file__))

from utils import log
from inspect_cli import inspect_package
from import_cli import import_package


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)

    pins = sub.add_parser("inspect", help="Inspecciona un paquete Appian")
    pins.add_argument("--base-url", required=True)
    pins.add_argument("--api-key", required=True)
    pins.add_argument("--package-path", required=True)
    pins.add_argument("--customization-path", default="", help="Ruta a .properties (opcional)")
    pins.add_argument("--admin-settings-path", default="", help="Ruta a Admin Console Settings .zip (opcional)")

    pimp = sub.add_parser("import", help="Importa/promueve un paquete (sin inspección)")
    pimp.add_argument("--base-url", required=True)
    pimp.add_argument("--api-key", required=True)
    pimp.add_argument("--package-path", required=True)
    pimp.add_argument("--customization-path", default="", help="Ruta a .properties (opcional)")
    pimp.add_argument("--admin-settings-path", default="", help="Ruta a Admin Console Settings .zip (opcional)")
    pimp.add_argument("--plugins-zip", default="", help="Ruta a ZIP de plug-ins (opcional)")
    pimp.add_argument("--name", default="", help="Nombre del deployment (opcional)")
    pimp.add_argument("--description", default="", help="Descripción del deployment (opcional)")
    pimp.add_argument("--dry-run", action="store_true")

    args = p.parse_args()

    if args.cmd == "inspect":
        customization = Path(args.customization_path).resolve() if args.customization_path else None
        admin_settings = Path(args.admin_settings_path).resolve() if args.admin_settings_path else None
        inspect_package(
            args.base_url,
            args.api_key,
            Path(args.package_path),
            customization,
            admin_settings,
        )
    elif args.cmd == "import":
        customization = Path(args.customization_path).resolve() if args.customization_path else None
        admin_settings = Path(args.admin_settings_path).resolve() if args.admin_settings_path else None
        plugins = Path(args.plugins_zip).resolve() if args.plugins_zip else None
        name = args.name or ""
        import_package(
            args.base_url,
            args.api_key,
            Path(args.package_path),
            args.dry_run,
            customization,
            admin_settings,
            plugins,
            name,
            args.description,
        )


if __name__ == "__main__":
    main()


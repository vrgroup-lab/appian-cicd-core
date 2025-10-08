#!/usr/bin/env python3
import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Optional, Dict

# Soportar ejecución directa del script
if __package__ is None:  # pragma: no cover
    sys.path.append(os.path.dirname(__file__))
from utils import log, _http
try:  # prefer relative when running as a package
    from .utils import _multipart_form  # type: ignore
except Exception:  # fallback when running as loose scripts
    from utils import _multipart_form


def _post_import(base_url: str, api_key: str, name: str, description: str, package_path: Path,
                 customization_path: Optional[Path] = None,
                 admin_settings_path: Optional[Path] = None,
                 plugins_zip: Optional[Path] = None) -> dict:
    url = f"{base_url.rstrip('/')}/suite/deployment-management/v2/deployments"
    json_obj: dict = {
        "name": name,
        "description": description,
        "packageFileName": package_path.name,
    }
    # multipart form-data con campos alineados al JSON
    files: dict = {"packageFileName": package_path}
    if customization_path:
        json_obj["customizationFileName"] = customization_path.name
        files["customizationFileName"] = customization_path
    if admin_settings_path:
        json_obj["adminConsoleSettingsFileName"] = admin_settings_path.name
        files["adminConsoleSettingsFileName"] = admin_settings_path
    if plugins_zip:
        json_obj["pluginsFileName"] = plugins_zip.name
        files["pluginsFileName"] = plugins_zip

    body, ctype = _multipart_form(json_obj, files)
    headers = {
        "appian-api-key": api_key,
        "Action-Type": "import",
        "Content-Type": ctype,
        "Accept": "application/json",
    }
    retries = int(os.environ.get("APPIAN_PROMOTE_IMPORT_RETRIES", "3"))
    delay_s = int(os.environ.get("APPIAN_PROMOTE_RETRY_DELAY", "10"))
    attempt = 0
    while True:
        attempt += 1
        try:
            raw, _ = _http("POST", url, headers, data=body, timeout=300)
            return json.loads(raw.decode("utf-8"))
        except RuntimeError as e:
            msg = str(e)
            transient = (
                "HTTP 500" in msg or
                "Network error" in msg or
                "handshake" in msg or
                "timed out" in msg
            )
            if attempt <= retries and transient:
                log(f"deploy.post=RETRY {attempt}/{retries} (transitorio: {msg.splitlines()[0]})")
                time.sleep(delay_s)
                continue
            raise


def _get_deployment(base_url: str, api_key: str, dep_uuid: str, url_hint: Optional[str] = None) -> dict:
    url = url_hint or f"{base_url.rstrip('/')}/suite/deployment-management/v2/deployments/{dep_uuid}"
    headers = {"appian-api-key": api_key, "Accept": "application/json"}
    raw, _ = _http("GET", url, headers, timeout=60)
    return json.loads(raw.decode("utf-8"))


def _get_deployment_log(base_url: str, api_key: str, dep_uuid: str) -> str:
    url = f"{base_url.rstrip('/')}/suite/deployment-management/v2/deployments/{dep_uuid}/log"
    headers = {"appian-api-key": api_key, "Accept": "text/plain"}
    raw, _ = _http("GET", url, headers, timeout=180)
    try:
        return raw.decode("utf-8")
    except Exception:
        return raw.decode("latin-1", "ignore")


def import_package(base_url: str, api_key: str, package_path: Path,
                   customization_path: Optional[Path] = None,
                   admin_settings_path: Optional[Path] = None,
                   plugins_zip: Optional[Path] = None,
                   name: Optional[str] = None,
                   description: str = "") -> Dict[str, object]:
    if not package_path.exists():
        raise FileNotFoundError(f"No existe el paquete: {package_path}")

    try:
        size = package_path.stat().st_size
        head = package_path.read_bytes()[:4]
        if size < 1024 or not (len(head) >= 2 and head[:2] == b"PK"):
            raise RuntimeError(
                f"El artifact no es un ZIP válido para Appian (size={size}B, magic={head!r})."
            )
    except Exception as e:
        if isinstance(e, RuntimeError):
            raise
        raise RuntimeError(f"No se pudo validar el ZIP del paquete: {e}")
    if customization_path and not customization_path.exists():
        raise FileNotFoundError(f"No existe customization file: {customization_path}")
    if admin_settings_path and not admin_settings_path.exists():
        raise FileNotFoundError(f"No existe admin console settings: {admin_settings_path}")
    if plugins_zip and not plugins_zip.exists():
        raise FileNotFoundError(f"No existe plugins zip: {plugins_zip}")

    max_wait_s = int(os.environ.get("APPIAN_PROMOTE_MAX_WAIT", "1800"))
    interval_s = int(os.environ.get("APPIAN_PROMOTE_POLL_INTERVAL", "5"))

    dep_name = name or f"Import {package_path.name}"
    dep_desc = description
    log("Iniciando import del paquete…")
    dep = _post_import(base_url, api_key, dep_name, dep_desc, package_path, customization_path, admin_settings_path, plugins_zip)
    dep_uuid = dep.get("uuid")
    dep_url = dep.get("url")
    if not dep_uuid:
        raise RuntimeError(f"Respuesta inesperada al iniciar import: {dep}")

    waited = 0
    final = None
    while True:
        st = _get_deployment(base_url, api_key, dep_uuid, dep_url)
        status = str(st.get("status", "")).upper()
        log(f"deploy.status={status} uuid={dep_uuid}")
        if status in (
            "COMPLETED",
            "COMPLETED_WITH_ERRORS",
            "COMPLETED_WITH_IMPORT_ERRORS",
            "COMPLETED_WITH_PUBLISH_ERRORS",
            "FAILED",
            "PENDING_REVIEW",
            "REJECTED",
        ):
            final = st
            break
        time.sleep(interval_s)
        waited += interval_s
        if waited > max_wait_s:
            raise RuntimeError("Timeout esperando import en Appian")

    final_status = str(final.get("status", "")).upper() if final else ""
    summary = final.get("summary") or {}
    log_url = summary.get("deploymentLogUrl") or final.get("deploymentLogUrl")

    def _print_log():
        try:
            if log_url:
                log("--- Deployment log (tail) ---")
                txt = _get_deployment_log(base_url, api_key, dep_uuid)
                lines = txt.splitlines()
                for ln in lines[-200:]:
                    log(ln)
                log("--- Fin deployment log ---")
        except Exception as e:
            log(f"No se pudo obtener deployment log: {e}")

    bad_statuses = {"FAILED", "REJECTED"}
    error_statuses = {"COMPLETED_WITH_ERRORS", "COMPLETED_WITH_IMPORT_ERRORS", "COMPLETED_WITH_PUBLISH_ERRORS"}

    if final_status in bad_statuses:
        _print_log()
        raise RuntimeError(f"Import FAILED: status={final_status}")
    if final_status in error_statuses:
        _print_log()
        raise RuntimeError(f"Import completado con errores: status={final_status}")

    objs = (summary.get("objects") or {})
    log(f"Import OK: objects.imported={objs.get('imported')} failed={objs.get('failed')} skipped={objs.get('skipped')}")
    return {"status": final_status, "uuid": dep_uuid or "", "deployment": final or {}}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--base-url", required=True)
    p.add_argument("--api-key", required=True)
    p.add_argument("--package-path", required=True)
    p.add_argument("--customization-path", default="")
    p.add_argument("--admin-settings-path", default="")
    p.add_argument("--plugins-zip", default="")
    p.add_argument("--name", default="")
    p.add_argument("--description", default="")
    args = p.parse_args()

    customization = Path(args.customization_path).resolve() if args.customization_path else None
    admin_settings = Path(args.admin_settings_path).resolve() if args.admin_settings_path else None
    plugins = Path(args.plugins_zip).resolve() if args.plugins_zip else None
    name = args.name or ""

    import_package(
        args.base_url,
        args.api_key,
        Path(args.package_path),
        customization,
        admin_settings,
        plugins,
        name,
        args.description,
    )


if __name__ == "__main__":
    main()

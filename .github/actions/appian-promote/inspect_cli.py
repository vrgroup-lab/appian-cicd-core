#!/usr/bin/env python3
import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Optional

# Soportar ejecución directa del script
if __package__ is None:  # pragma: no cover
    sys.path.append(os.path.dirname(__file__))
from utils import log, _http, _multipart_form


def _post_inspection(base_url: str, api_key: str, package_path: Path,
                     customization_path: Optional[Path] = None,
                     admin_settings_path: Optional[Path] = None) -> dict:
    url = f"{base_url.rstrip('/')}/suite/deployment-management/v2/inspections"
    json_obj = {"packageFileName": package_path.name}
    files = {"packageFileName": package_path}
    if customization_path:
        files["customizationFileName"] = customization_path
    if admin_settings_path:
        files["adminConsoleSettingsFileName"] = admin_settings_path

    try:
        log(f"/inspections: package={package_path.name} size={package_path.stat().st_size}B" + (
            f", icf={customization_path.name}" if customization_path else "") + (
            f", admin={admin_settings_path.name}" if admin_settings_path else ""))
    except Exception:
        pass

    body, ctype = _multipart_form(json_obj, files)
    headers = {"appian-api-key": api_key, "Content-Type": ctype, "Accept": "application/json"}
    raw, _ = _http("POST", url, headers, data=body, timeout=600)
    return json.loads(raw.decode("utf-8"))


def _get_inspection(base_url: str, api_key: str, insp_uuid: str, url_hint: Optional[str] = None) -> dict:
    url = (url_hint or f"{base_url.rstrip('/')}/suite/deployment-management/v2/inspections/{insp_uuid}").rstrip('/')
    headers = {"appian-api-key": api_key, "Accept": "application/json"}
    raw, _ = _http("GET", url, headers, timeout=60)
    return json.loads(raw.decode("utf-8"))


def inspect_package(base_url: str, api_key: str, package_path: Path,
                    customization_path: Optional[Path] = None,
                    admin_settings_path: Optional[Path] = None):
    if not package_path.exists():
        raise FileNotFoundError(f"No existe el paquete: {package_path}")
    # Validación básica
    size = package_path.stat().st_size
    head = package_path.read_bytes()[:4]
    if size < 1024 or not (len(head) >= 2 and head[:2] == b"PK"):
        raise RuntimeError(f"El artifact no es un ZIP válido para Appian (size={size}B, magic={head!r}).")

    max_wait_s = int(os.environ.get("APPIAN_PROMOTE_MAX_WAIT", "1800"))
    interval_s = int(os.environ.get("APPIAN_PROMOTE_POLL_INTERVAL", "5"))
    max_err_retries = int(os.environ.get("APPIAN_PROMOTE_INSPECTION_RETRIES", "5"))

    log("Iniciando inspección del paquete…")
    insp = _post_inspection(base_url, api_key, package_path, customization_path, admin_settings_path)
    insp_uuid = insp.get("uuid")
    insp_url = insp.get("url")
    if not insp_uuid:
        raise RuntimeError(f"Respuesta inesperada de inspección: {insp}")

    waited = 0
    retries_500 = 0
    retries_net = 0
    while True:
        try:
            res = _get_inspection(base_url, api_key, insp_uuid, insp_url)
        except RuntimeError as e:
            msg = str(e)
            if "HTTP 404" in msg:
                log(f"inspect.status=PENDING uuid={insp_uuid} (404: no registrada aún; reintentando)")
                time.sleep(interval_s)
                waited += interval_s
                if waited > max_wait_s:
                    raise RuntimeError("Timeout esperando inspección de Appian (404 persistente)")
                continue
            # Appian a veces responde 500 APNX-1-4552-005 cuando la inspección terminó
            # pero los datos aún no están listos. Reintentamos como si fuera PENDING.
            if "HTTP 500" in msg and ("APNX-1-4552-005" in msg or "/inspections/" in msg):
                retries_500 += 1
                if retries_500 > max_err_retries:
                    raise RuntimeError(
                        f"Inspección abortada: demasiados 500 APNX-1-4552-005 consecutivos (>{max_err_retries})."
                    )
                log(f"inspect.status=PENDING uuid={insp_uuid} (500 APNX-1-4552-005: sin información; retry {retries_500}/{max_err_retries})")
                time.sleep(interval_s)
                waited += interval_s
                if waited > max_wait_s:
                    raise RuntimeError("Timeout esperando inspección de Appian (500 persistente)")
                continue
            # Reintento ante fallas de red/handshake (URLError, timeouts)
            if "Network error" in msg or "handshake" in msg or "timed out" in msg:
                retries_net += 1
                if retries_net > max_err_retries:
                    raise RuntimeError(
                        f"Inspección abortada: demasiados errores de red consecutivos (>{max_err_retries})."
                    )
                log(f"inspect.status=PENDING uuid={insp_uuid} (red/timeout; retry {retries_net}/{max_err_retries})")
                time.sleep(interval_s)
                waited += interval_s
                if waited > max_wait_s:
                    raise RuntimeError("Timeout esperando inspección de Appian (problemas de red persistentes)")
                continue
            raise
        status = str(res.get("status", "")).upper()
        log(f"inspect.status={status} uuid={insp_uuid}")
        # Resetear contadores de errores transitorios al recibir respuesta válida
        retries_500 = 0
        retries_net = 0
        if status in ("COMPLETED", "FAILED"):
            break
        time.sleep(interval_s)
        waited += interval_s
        if waited > max_wait_s:
            raise RuntimeError("Timeout esperando inspección de Appian")

    summary = (res.get("summary") or {})
    problems = (summary.get("problems") or {})
    total_errors = int(problems.get("totalErrors") or 0)
    total_warnings = int(problems.get("totalWarnings") or 0)
    if total_warnings:
        log(f"Inspección con warnings: {total_warnings}")
    if total_errors > 0:
        errors = problems.get("errors") or []
        log("Inspección encontró errores; abortando. Detalle (primeros 10):")
        for e in errors[:10]:
            log(f"- {e.get('objectName')} ({e.get('objectUuid')}): {e.get('errorMessage')}")
        raise RuntimeError("Inspección fallida (hay errores)")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--base-url", required=True)
    p.add_argument("--api-key", required=True)
    p.add_argument("--package-path", required=True)
    p.add_argument("--customization-path", default="")
    p.add_argument("--admin-settings-path", default="")
    args = p.parse_args()

    customization = Path(args.customization_path).resolve() if args.customization_path else None
    admin_settings = Path(args.admin_settings_path).resolve() if args.admin_settings_path else None
    inspect_package(
        args.base_url,
        args.api_key,
        Path(args.package_path),
        customization,
        admin_settings,
    )


if __name__ == "__main__":
    main()

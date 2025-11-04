#!/usr/bin/env python3
import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def log(msg: str):
    print(msg, file=sys.stderr, flush=True)


def http_json(method: str, url: str, headers: dict, body: dict | None = None):
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = Request(url, data=data, method=method)
    for k, v in headers.items():
        req.add_header(k, v)
    if body is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urlopen(req, timeout=60) as resp:
            ct = resp.headers.get("Content-Type", "")
            raw = resp.read()
            if "application/json" in ct:
                return json.loads(raw.decode("utf-8"))
            return raw
    except HTTPError as e:
        raise RuntimeError(f"HTTP {e.code} on {url}: {e.read().decode('utf-8', 'ignore')}") from e
    except URLError as e:
        raise RuntimeError(f"Network error on {url}: {e}") from e


def _post_export_start(base_url: str, api_key: str, kind: str, resource_id: str, name: str | None = None, description: str | None = None) -> dict:
    # Build multipart/form-data with a single 'json' field
    url = f"{base_url.rstrip('/')}/suite/deployment-management/v2/deployments"
    boundary = f"----appianboundary{int(time.time())}"
    # Appian API expects exportType values: "application" or "package".
    # Allow callers to pass the short alias "app" and normalize here.
    export_type = "application" if kind.lower() in ("app", "application") else kind
    payload = {
        "exportType": export_type,
        "uuids": [resource_id],
    }
    if name:
        payload["name"] = name
    if description:
        payload["description"] = description

    part = (
        f"--{boundary}\r\n"
        "Content-Disposition: form-data; name=\"json\"\r\n"
        "Content-Type: application/json\r\n\r\n"
        f"{json.dumps(payload)}\r\n"
        f"--{boundary}--\r\n"
    ).encode("utf-8")

    req = Request(url, data=part, method="POST")
    req.add_header("appian-api-key", api_key)
    req.add_header("Action-Type", "export")
    req.add_header("Accept", "application/json")
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    try:
        with urlopen(req, timeout=60) as resp:
            raw = resp.read()
            return json.loads(raw.decode("utf-8"))
    except HTTPError as e:
        raise RuntimeError(f"HTTP {e.code} on export start: {e.read().decode('utf-8', 'ignore')}") from e
    except URLError as e:
        raise RuntimeError(f"Network error on export start: {e}") from e


def _get_deployment_status(base_url: str, api_key: str, dep_uuid: str, url_hint: str | None = None) -> dict:
    url = url_hint or f"{base_url.rstrip('/')}/suite/deployment-management/v2/deployments/{dep_uuid}"
    req = Request(url, method="GET")
    req.add_header("appian-api-key", api_key)
    req.add_header("Accept", "application/json")
    try:
        with urlopen(req, timeout=60) as resp:
            raw = resp.read()
            return json.loads(raw.decode("utf-8"))
    except HTTPError as e:
        raise RuntimeError(f"HTTP {e.code} on status: {e.read().decode('utf-8', 'ignore')}") from e
    except URLError as e:
        raise RuntimeError(f"Network error on status: {e}") from e


def _attempt_download(url: str, api_key: str, out_path: Path) -> bool:
    req = Request(url, method="GET")
    req.add_header("appian-api-key", api_key)
    req.add_header("Accept", "application/zip")
    try:
        with urlopen(req, timeout=180) as resp:
            ct = resp.headers.get("Content-Type", "")
            data = resp.read()
            # Aceptar solo si es un ZIP válido por header o firma 'PK'
            is_zip_header = "application/zip" in ct.lower()
            is_zip_magic = len(data) >= 4 and data[:2] == b"PK"
            if is_zip_header or is_zip_magic:
                out_path.parent.mkdir(parents=True, exist_ok=True)
                out_path.write_bytes(data)
                return True
            return False
    except HTTPError as e:
        # 404/400: probamos siguiente candidato
        return False
    except URLError:
        return False


def _download_package_from_results(base_url: str, api_key: str, results: dict, dep_uuid: str, status_url: str | None, out_path: Path):
    base = base_url.rstrip('/')
    candidates: list[str] = []
    # Preferir el campo explícito devuelto por v2
    pkg = results.get("packageZip")
    if isinstance(pkg, str) and pkg:
        candidates.append(pkg.rstrip('/'))
    # Variantes comunes por si falta barra
    if isinstance(pkg, str) and pkg:
        p = pkg.rstrip('/')
        if not p.endswith("/package-zip"):
            candidates.append(p + "/package-zip")
    # Fallbacks conocidos
    if status_url:
        s = status_url.rstrip('/')
        candidates.extend([
            f"{s}/package-zip",
            f"{s}/package",
            f"{s}/download",
            f"{s}?download=true",
        ])
    candidates.extend([
        f"{base}/suite/deployment-management/v2/deployments/{dep_uuid}/package-zip",
        f"{base}/suite/deployment-management/v2/deployments/{dep_uuid}/package",
        f"{base}/suite/deployment-management/v2/deployments/{dep_uuid}/download",
    ])
    tried: list[str] = []
    for u in candidates:
        if not u:
            continue
        tried.append(u)
        if _attempt_download(u, api_key, out_path):
            return
    raise RuntimeError("No se pudo descargar el ZIP de export. URLs probadas: " + "; ".join(tried))


def _ensure_absolute_url(base_url: str, url: str) -> str:
    if not url:
        return url
    if url.startswith("http://") or url.startswith("https://"):
        return url
    if url.startswith('/'):
        return f"{base_url.rstrip('/')}{url}"
    return f"{base_url.rstrip('/')}/{url}"


def _sanitize_filename(name: str, fallback: str) -> str:
    base = Path(name).name.strip()
    if not base:
        base = fallback
    base = base.replace('\x00', '')
    # Reemplazamos cualquier caracter no alfanumérico relevante para evitar path traversal
    base = re.sub(r"[^A-Za-z0-9._-]+", "_", base)
    if not base:
        base = fallback
    if base.startswith('.'):
        base = f"_{base.lstrip('.')}"
    return base


def _download_binary(url: str, api_key: str, out_path: Path, accept: Optional[str] = None) -> str:
    req = Request(url, method="GET")
    req.add_header("appian-api-key", api_key)
    if accept:
        req.add_header("Accept", accept)
    try:
        with urlopen(req, timeout=180) as resp:
            data = resp.read()
    except HTTPError as e:
        raise RuntimeError(f"HTTP {e.code} al descargar recurso ({url}): {e.read().decode('utf-8', 'ignore')}") from e
    except URLError as e:
        raise RuntimeError(f"Network error al descargar recurso ({url}): {e}") from e
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(data)
    return str(out_path.resolve())


def _download_database_scripts(base_url: str, api_key: str, results: Dict[str, Any], out_dir: Path) -> List[Dict[str, Any]]:
    scripts: List[Dict[str, Any]] = []
    entries = results.get("databaseScripts") or []
    if not isinstance(entries, list):
        return scripts
    target_dir = out_dir / "db-scripts"
    for idx, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict):
            continue
        url = entry.get("url")
        if not url:
            continue
        safe_url = _ensure_absolute_url(base_url, str(url))
        order = entry.get("orderId")
        fallback_name = f"script_{idx}.sql"
        original_name = str(entry.get("filename") or entry.get("fileName") or fallback_name)
        safe_name = _sanitize_filename(original_name, fallback_name)
        prefix = ""
        try:
            if order is None:
                raise ValueError
            order_int = int(order)
            prefix = f"{order_int:03d}-"
        except Exception:
            prefix = f"{idx:03d}-"
            order_int = None
        dest = target_dir / f"{prefix}{safe_name}"
        path = _download_binary(safe_url, api_key, dest)
        scripts.append({
            "path": path,
            "fileName": original_name,
            "orderId": order if isinstance(order, int) else order_int,
            "url": safe_url,
        })
    return scripts


def _download_optional_file(url: Optional[Any], base_url: str, api_key: str, dest: Path, accept: Optional[str] = None) -> str:
    if not url:
        return ""
    safe_url = _ensure_absolute_url(base_url, str(url))
    return _download_binary(safe_url, api_key, dest, accept=accept)


def export_resource(base_url: str, api_key: str, kind: str, resource_id: str, out_path: Path) -> Dict[str, Any]:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    package_abs = str(out_path.resolve())
    artifact_dir = str(out_path.resolve().parent)
    result: Dict[str, Any] = {
        "package_path": package_abs,
        "artifact_dir": artifact_dir,
        "database_scripts": [],
        "plugins_zip": "",
        "customization_file": "",
        "customization_template": "",
        "downloaded_files": [],
        "deployment_uuid": "",
        "deployment_status": "",
        "raw_response": {},
    }

    start = _post_export_start(base_url, api_key, kind, resource_id)
    dep_uuid = start.get("uuid")
    status_url = start.get("url")
    if not dep_uuid:
        raise RuntimeError(f"Respuesta inesperada al iniciar export: {start}")
    result["deployment_uuid"] = dep_uuid

    max_wait_s = int(os.environ.get("APPIAN_EXPORT_MAX_WAIT", "900"))  # 15 min por defecto
    interval = int(os.environ.get("APPIAN_EXPORT_POLL_INTERVAL", "5"))
    waited = 0
    final: Optional[Dict[str, Any]] = None
    status: str = ""
    while True:
        st = _get_deployment_status(base_url, api_key, dep_uuid, status_url)
        status = str(st.get("status", "")).upper()
        log(f"status={status} uuid={dep_uuid}")
        if status in ("COMPLETED", "COMPLETED_WITH_EXPORT_ERRORS", "FAILED"):
            final = st
            break
        time.sleep(interval)
        waited += interval
        if waited > max_wait_s:
            raise RuntimeError("Timeout esperando export en Appian")

    result["deployment_status"] = status

    if status in ("FAILED", "COMPLETED_WITH_EXPORT_ERRORS"):
        raise RuntimeError(f"Export con errores/failed: {final}")

    final_payload: Dict[str, Any] = final or {}
    result["raw_response"] = final_payload

    _download_package_from_results(base_url, api_key, final_payload, dep_uuid, status_url, out_path)
    package_abs = str(out_path.resolve())
    result["package_path"] = package_abs

    downloaded: List[str] = [package_abs]

    base_dir = out_path.parent

    db_scripts = _download_database_scripts(base_url, api_key, final_payload, base_dir)
    if db_scripts:
        result["database_scripts"] = db_scripts
        downloaded.extend([entry["path"] for entry in db_scripts])

    plugins_dest = base_dir / "plugins" / "plugins.zip"
    plugins_path = _download_optional_file(final_payload.get("pluginsZip"), base_url, api_key, plugins_dest)
    if plugins_path:
        result["plugins_zip"] = plugins_path
        downloaded.append(plugins_path)

    customization_dest = base_dir / "customization" / "customization.properties"
    customization_path = _download_optional_file(final_payload.get("customizationFile"), base_url, api_key, customization_dest)
    if customization_path:
        result["customization_file"] = customization_path
        downloaded.append(customization_path)

    customization_template_dest = base_dir / "customization" / "customization-template.properties"
    customization_template_path = _download_optional_file(final_payload.get("customizationFileTemplate"), base_url, api_key, customization_template_dest)
    if customization_template_path:
        result["customization_template"] = customization_template_path
        downloaded.append(customization_template_path)

    result["downloaded_files"] = downloaded

    return result


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)

    pe = sub.add_parser("export", help="Exporta app o package")
    pe.add_argument("--base-url", required=True)
    pe.add_argument("--api-key", required=True)
    # Accept both "app" alias and full "application" for convenience
    pe.add_argument("--kind", choices=["app", "application", "package"], required=True)
    pe.add_argument("--rid", required=True, help="resource_id")
    pe.add_argument("--name", default="", help="nombre amigable para archivo")
    pe.add_argument("--outdir", default="artifacts")

    args = p.parse_args()

    if args.cmd == "export":
        # Compose filename determinísticamente
        nm = args.name or args.rid
        fname = f"{args.kind}-{args.rid}-{nm}.zip"
        out_path = Path(args.outdir) / fname
        info = export_resource(args.base_url, args.api_key, args.kind, args.rid, out_path)
        print(json.dumps(info))


if __name__ == "__main__":
    main()

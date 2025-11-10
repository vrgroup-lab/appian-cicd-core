#!/usr/bin/env python3
"""Shared utilities for Appian promotion scripts."""

import json
import sys
import uuid as _uuid
from pathlib import Path
from typing import Dict, Optional, Tuple, Union
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def log(msg: str) -> None:
    """Emit a log line compatible with GitHub Actions."""
    print(msg, flush=True, file=sys.stderr)


def _http(
    method: str,
    url: str,
    headers: dict,
    data: bytes | None = None,
    timeout: int = 60,
) -> Tuple[bytes, Dict[str, str]]:
    req = Request(url, data=data, method=method)
    for k, v in headers.items():
        req.add_header(k, v)
    try:
        with urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            hdrs = {k.lower(): v for k, v in resp.headers.items()}
            return raw, hdrs
    except HTTPError as e:
        message = e.read().decode("utf-8", "ignore")
        raise RuntimeError(f"HTTP {e.code} on {url}: {message}") from e
    except URLError as e:
        raise RuntimeError(f"Network error on {url}: {e}") from e


def http_json(method: str, url: str, headers: dict, body: dict | None = None, timeout: int = 60):
    data = None if body is None else json.dumps(body).encode("utf-8")
    h = dict(headers)
    if body is not None:
        h["Content-Type"] = "application/json"
    raw, resp_headers = _http(method, url, h, data, timeout=timeout)
    ct = resp_headers.get("content-type", "")
    if "application/json" in ct:
        return json.loads(raw.decode("utf-8"))
    try:
        return json.loads(raw.decode("utf-8"))
    except Exception:
        return {"raw": raw.decode("utf-8", "ignore")}


def _guess_ct(path: Path) -> str:
    name = path.name.lower()
    if name.endswith(".zip"):
        return "application/zip"
    if name.endswith(".properties"):
        return "text/plain"
    if name.endswith(".sql") or name.endswith(".ddl"):
        return "text/plain"
    return "application/octet-stream"


FileEntry = Union[Path, Tuple[Path, Optional[str]]]


def _multipart_form(json_part: dict, files: Dict[str, FileEntry]) -> Tuple[bytes, str]:
    boundary = f"----AppianBoundary{_uuid.uuid4().hex}"
    parts: list[bytes] = []

    json_bytes = json.dumps(json_part).encode("utf-8")
    parts.append((
        f"--{boundary}\r\n"
        f"Content-Disposition: form-data; name=\"json\"\r\n"
        f"Content-Type: application/json\r\n\r\n"
    ).encode("utf-8") + json_bytes + b"\r\n")

    for field, entry in files.items():
        if isinstance(entry, tuple):
            path, override_name = entry
        else:
            path, override_name = entry, None
        data = path.read_bytes()
        ct = _guess_ct(path)
        filename = override_name or path.name
        disp = (
            f"--{boundary}\r\n"
            f"Content-Disposition: form-data; name=\"{field}\"; filename=\"{filename}\"\r\n"
            f"Content-Type: {ct}\r\n\r\n"
        ).encode("utf-8")
        parts.append(disp + data + b"\r\n")

    parts.append(f"--{boundary}--\r\n".encode("utf-8"))
    body = b"".join(parts)
    content_type = f"multipart/form-data; boundary={boundary}"
    return body, content_type

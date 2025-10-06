#!/usr/bin/env bash
set -euo pipefail

# Placeholder script (no-op) for future real Appian promote/import via API.
# Arguments (by env vars):
#   APPIAN_API_KEY_TARGET - required
#   PACKAGE_PATH          - required
#   DRY_RUN               - optional

if [[ -z "${APPIAN_API_KEY_TARGET:-}" || -z "${PACKAGE_PATH:-}" ]]; then
  echo "Usage error: missing required env vars" >&2
  exit 2
fi

if [[ ! -f "$PACKAGE_PATH" ]]; then
  echo "No se encuentra el paquete a importar: $PACKAGE_PATH" >&2
  exit 3
fi

echo "[MVP] Simulando importación en entorno target"
if [[ "${DRY_RUN:-false}" == "true" ]]; then
  echo "[MVP] dry_run=true — no se llama API"
fi

echo "[MVP] Import OK (simulado)"


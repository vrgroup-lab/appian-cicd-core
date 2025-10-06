#!/usr/bin/env bash
set -euo pipefail

# Placeholder script (no-op) for future real Appian export via API.
# Arguments (by env vars):
#   APPIAN_API_KEY  - required
#   APP_SLUG        - required
#   PACKAGE_NAME    - required
#   OUT_FILE        - required
#   DRY_RUN         - optional (true/false)

if [[ -z "${APPIAN_API_KEY:-}" || -z "${APP_SLUG:-}" || -z "${PACKAGE_NAME:-}" || -z "${OUT_FILE:-}" ]]; then
  echo "Usage error: missing required env vars" >&2
  exit 2
fi

echo "[MVP] Simulando exportación de '$APP_SLUG' (paquete '$PACKAGE_NAME')"
if [[ "${DRY_RUN:-false}" == "true" ]]; then
  echo "[MVP] dry_run=true — no se llama API"
fi

mkdir -p "$(dirname "$OUT_FILE")"
echo "fake binary" > "$OUT_FILE"
echo "[MVP] Artefacto: $OUT_FILE"


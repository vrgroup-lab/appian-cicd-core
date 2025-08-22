#!/usr/bin/env bash
set -euo pipefail

# Usage:
# ./scripts/appian_resolve_package.sh \
#   --base-url https://example.appiancloud.com \
#   --api-key "$APPIAN_API_KEY" \
#   --app-uuid <application uuid> \
#   [--package-name <name>]

command -v jq >/dev/null 2>&1 || { echo "jq is required"; exit 127; }
command -v curl >/dev/null 2>&1 || { echo "curl is required"; exit 127; }

BASE_URL=""
API_KEY=""
APP_UUID=""
PACKAGE_NAME=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --base-url) BASE_URL="$2"; shift 2;;
    --api-key) API_KEY="$2"; shift 2;;
    --app-uuid) APP_UUID="$2"; shift 2;;
    --package-name) PACKAGE_NAME="$2"; shift 2;;
    *) echo "Unknown arg: $1" >&2; exit 2;;
  esac
done

if [[ -z "$BASE_URL" || -z "$API_KEY" || -z "$APP_UUID" ]]; then
  echo "Missing required args. base-url, api-key and app-uuid are required." >&2
  exit 2
fi

RES=$(curl -sS --fail-with-body --connect-timeout 10 --max-time 60 -X GET \
  -H "appian-api-key: ${API_KEY}" \
  "${BASE_URL%/}/suite/deployment-management/v2/applications/${APP_UUID}/packages" \
  || true)

if [[ -z "${RES:-}" ]]; then
  echo "Failed to list packages" >&2
  exit 1
fi

if [[ -n "$PACKAGE_NAME" ]]; then
  PKG_UUID=$(echo "$RES" | jq -r --arg name "$PACKAGE_NAME" '.packages[] | select(.name == $name) | .uuid' | head -n1)
else
  PKG_UUID=$(echo "$RES" | jq -r '.packages[0].uuid // empty')
fi

if [[ -z "$PKG_UUID" ]]; then
  echo "Package not found" >&2
  exit 1
fi

echo "$PKG_UUID"

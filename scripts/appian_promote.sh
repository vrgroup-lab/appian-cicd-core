#!/usr/bin/env bash
set -euo pipefail

# Usage:
# ./scripts/appian_promote.sh \
#   --base-url https://example.appiancloud.com \
#   --api-key "$APPIAN_API_KEY" \
#   --package-path ./package.zip \
#   --poll-timeout-sec 600 \
#   --poll-interval-sec 5

command -v jq >/dev/null 2>&1 || { echo "jq is required"; exit 127; }
command -v curl >/dev/null 2>&1 || { echo "curl is required"; exit 127; }

BASE_URL=""
API_KEY=""
PACKAGE_PATH=""
POLL_TIMEOUT=600
POLL_INTERVAL=5

while [[ $# -gt 0 ]]; do
  case "$1" in
    --base-url) BASE_URL="$2"; shift 2;;
    --api-key) API_KEY="$2"; shift 2;;
    --package-path) PACKAGE_PATH="$2"; shift 2;;
    --poll-timeout-sec) POLL_TIMEOUT="$2"; shift 2;;
    --poll-interval-sec) POLL_INTERVAL="$2"; shift 2;;
    *) echo "Unknown arg: $1" >&2; exit 2;;
  esac
done

if [[ -z "$BASE_URL" || -z "$API_KEY" || -z "$PACKAGE_PATH" ]]; then
  echo "Missing required args. base-url, api-key and package-path are required." >&2
  exit 2
fi

if [[ ! -f "$PACKAGE_PATH" ]]; then
  echo "Package file not found: $PACKAGE_PATH" >&2
  exit 1
fi

echo "Trigger import from package: $PACKAGE_PATH"
CREATE_RES=$(curl -sS --fail-with-body --connect-timeout 10 --max-time 60 -X POST \
  -H "appian-api-key: ${API_KEY}" \
  -H "Action-Type: import" \
  -F "file=@${PACKAGE_PATH};type=application/zip" \
  "${BASE_URL%/}/suite/deployment-management/v2/deployments" \
  || true)

if [[ -z "${CREATE_RES:-}" ]]; then
  echo "Failed to start import (empty response)."
  exit 1
fi

DEP_UUID=$(echo "$CREATE_RES" | jq -r '.uuid // empty')
STATUS=$(echo "$CREATE_RES" | jq -r '.status // empty')
URL=$(echo "$CREATE_RES" | jq -r '.url // empty')

if [[ -z "$DEP_UUID" ]]; then
  echo "Failed to start import. Response:"
  (echo "$CREATE_RES" | jq .) || echo "$CREATE_RES"
  exit 1
fi

echo "Import started: uuid=${DEP_UUID} status=${STATUS}"
[[ -n "$URL" && "$URL" != "null" ]] && echo "Details URL: ${URL}"

START_TS=$(date +%s)
CUR_STATUS="$STATUS"

while true; do
  GET_RES=$(curl -sS --fail-with-body --connect-timeout 10 --max-time 60 -X GET \
    -H "appian-api-key: ${API_KEY}" \
    "${BASE_URL%/}/suite/deployment-management/v2/deployments/${DEP_UUID}/" \
    || true)

  if [[ -z "${GET_RES:-}" ]]; then
    echo "Empty response while polling. Will continue..."
    CUR_STATUS="UNKNOWN"
  else
    CUR_STATUS=$(echo "$GET_RES" | jq -r '.status // "UNKNOWN"')
  fi

  echo "Status: $CUR_STATUS"

  case "$CUR_STATUS" in
    IN_PROGRESS|PENDING_REVIEW)
      :
      ;;
    *)
      echo "Final status: $CUR_STATUS"
      (echo "$GET_RES" | jq .) || echo "$GET_RES"
      break
      ;;
  esac

  NOW_TS=$(date +%s)
  if (( NOW_TS - START_TS > POLL_TIMEOUT )); then
    echo "Timeout waiting for import to finish (${POLL_TIMEOUT}s)" >&2
    (echo "$GET_RES" | jq .) || echo "$GET_RES"
    exit 1
  fi
  sleep "$POLL_INTERVAL"
done

if [[ "$CUR_STATUS" != "COMPLETED" ]]; then
  echo "Import finished with non-success status ($CUR_STATUS)"
  exit 1
fi

echo "Import finished OK ($CUR_STATUS)"

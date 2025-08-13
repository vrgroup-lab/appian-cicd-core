#!/usr/bin/env bash
set -euo pipefail

# Usage:
# ./scripts/appian_export.sh \
#   --base-url https://vrgroupdemo.appiancloud.com \
#   --api-key "$APPIAN_API_KEY" \
#   --export-type application|package \
#   --uuid "$UUID" \
#   --name "Optional name" \
#   --description "Optional description" \
#   --poll-timeout-sec 600 \
#   --poll-interval-sec 5 \
#   --download-out ./out

# ---- sanity checks
command -v jq >/dev/null 2>&1 || { echo "jq is required"; exit 127; }
command -v curl >/dev/null 2>&1 || { echo "curl is required"; exit 127; }

BASE_URL=""
API_KEY=""
EXPORT_TYPE=""
UUID=""
NAME=""
DESC=""
POLL_TIMEOUT=600
POLL_INTERVAL=5
DOWNLOAD_OUT=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --base-url) BASE_URL="$2"; shift 2;;
    --api-key) API_KEY="$2"; shift 2;;
    --export-type) EXPORT_TYPE="$2"; shift 2;;
    --uuid) UUID="$2"; shift 2;;
    --name) NAME="$2"; shift 2;;
    --description) DESC="$2"; shift 2;;
    --poll-timeout-sec) POLL_TIMEOUT="$2"; shift 2;;
    --poll-interval-sec) POLL_INTERVAL="$2"; shift 2;;
    --download-out) DOWNLOAD_OUT="$2"; shift 2;;
    *) echo "Unknown arg: $1" >&2; exit 2;;
  esac
done

if [[ -z "$BASE_URL" || -z "$API_KEY" || -z "$EXPORT_TYPE" || -z "$UUID" ]]; then
  echo "Missing required args. base-url, api-key, export-type, uuid are required." >&2
  exit 2
fi

if [[ "$EXPORT_TYPE" != "application" && "$EXPORT_TYPE" != "package" ]]; then
  echo "export-type must be 'application' or 'package'." >&2
  exit 2
fi

JSON_PAYLOAD=$(jq -n \
  --arg et "$EXPORT_TYPE" \
  --arg uuid "$UUID" \
  --arg name "${NAME:-}" \
  --arg desc "${DESC:-}" '
  {
    exportType: $et,
    uuids: [$uuid]
  }
  + ( ($name|length)  > 0 ? {name: $name} : {} )
  + ( ($desc|length)  > 0 ? {description: $desc} : {} )
')

echo "Trigger export: type=$EXPORT_TYPE uuid=$UUID"
CREATE_RES=$(curl -sS --fail-with-body --connect-timeout 10 --max-time 60 -X POST \
  -H "appian-api-key: ${API_KEY}" \
  -H "Action-Type: export" \
  -F "json=${JSON_PAYLOAD};type=application/json" \
  "${BASE_URL%/}/suite/deployment-management/v2/deployments" \
  || true)

# Si curl falló (4xx/5xx) CREATE_RES puede estar vacío; intentamos imprimir algo útil
if [[ -z "${CREATE_RES:-}" ]]; then
  echo "Failed to start export (empty response)."
  exit 1
fi

DEP_UUID=$(echo "$CREATE_RES" | jq -r '.uuid // empty')
STATUS=$(echo "$CREATE_RES" | jq -r '.status // empty')
URL=$(echo "$CREATE_RES" | jq -r '.url // empty')

if [[ -z "$DEP_UUID" ]]; then
  echo "Failed to start export. Response:"
  (echo "$CREATE_RES" | jq .) || echo "$CREATE_RES"
  exit 1
fi

echo "Export started: uuid=${DEP_UUID} status=${STATUS}"
[[ -n "$URL" && "$URL" != "null" ]] && echo "Details URL: ${URL}"

# Poll until completion (success only on COMPLETED)
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
    echo "Timeout waiting for export to finish (${POLL_TIMEOUT}s)" >&2
    (echo "$GET_RES" | jq .) || echo "$GET_RES"
    exit 1
  fi
  sleep "$POLL_INTERVAL"
done

# If package export and download requested, pull artifacts (packageZip, pluginsZip, db scripts, etc.)
if [[ "$EXPORT_TYPE" == "package" && -n "$DOWNLOAD_OUT" ]]; then
  mkdir -p "$DOWNLOAD_OUT"
  PKG_ZIP=$(echo "$GET_RES" | jq -r '.packageZip // empty')
  if [[ -n "$PKG_ZIP" && "$PKG_ZIP" != "null" ]]; then
    echo "Downloading package zip..."
    curl -sS --fail-with-body -H "appian-api-key: ${API_KEY}" -o "${DOWNLOAD_OUT%/}/package.zip" "$PKG_ZIP" || true
  fi

  PLUGINS_ZIP=$(echo "$GET_RES" | jq -r '.pluginsZip // empty')
  if [[ -n "$PLUGINS_ZIP" && "$PLUGINS_ZIP" != "null" ]]; then
    echo "Downloading plugins zip..."
    curl -sS --fail-with-body -H "appian-api-key: ${API_KEY}" -o "${DOWNLOAD_OUT%/}/plugins.zip" "$PLUGINS_ZIP" || true
  fi

  # Database scripts (array)
  DB_COUNT=$(echo "$GET_RES" | jq -r '.databaseScripts | length // 0')
  if (( DB_COUNT > 0 )); then
    mkdir -p "${DOWNLOAD_OUT%/}/db-scripts"
    for i in $(seq 0 $((DB_COUNT-1))); do
      URLI=$(echo "$GET_RES" | jq -r ".databaseScripts[$i].url // empty")
      NAMEI=$(echo "$GET_RES" | jq -r ".databaseScripts[$i].fileName // \"db-${i}.sql\"")
      if [[ -n "$URLI" && "$URLI" != "null" ]]; then
        curl -sS --fail-with-body -H "appian-api-key: ${API_KEY}" -o "${DOWNLOAD_OUT%/}/db-scripts/${NAMEI}" "$URLI" || true
      fi
    done
  fi
fi

# Exit non-zero unless COMPLETED (stricto)
if [[ "$CUR_STATUS" != "COMPLETED" ]]; then
  echo "Export finished with non-success status ($CUR_STATUS)"
  exit 1
fi

echo "Export finished OK ($CUR_STATUS)"
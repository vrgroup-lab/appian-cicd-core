#!/usr/bin/env bash
set -euo pipefail

# Map an environment name to its Appian base URL using
# environment variables defined as APPIAN_<NAME>_URL.
# Example: for "dev" it reads APPIAN_DEV_URL.

if [[ $# -ne 1 ]]; then
  echo "usage: $0 <environment-name>" >&2
  exit 1
fi

ENV_NAME="$1"
VAR_NAME="APPIAN_${ENV_NAME^^}_URL"
URL="${!VAR_NAME:-}"

if [[ -z "$URL" ]]; then
  echo "environment '$ENV_NAME' not configured (missing $VAR_NAME)" >&2
  exit 1
fi

echo "$URL"

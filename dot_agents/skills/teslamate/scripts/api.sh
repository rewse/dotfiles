#!/usr/bin/env bash
# GET a Grafana HTTP API path and print the JSON response.
#
# Usage: bash api.sh /api/search?type=dash-db
#        bash api.sh /api/dashboards/uid/<uid>
#
# Exits 1 with the response on stderr for a non-2xx status.
set -euo pipefail

# Shells do not export these, so other commands never inherit the token;
# read them from the file chezmoi renders.
environment="${XDG_CONFIG_HOME:-${HOME}/.config}/environment/teslamate.sh"
if [[ -r "${environment}" ]]; then
  # shellcheck source=/dev/null  # rendered from a template by chezmoi apply
  source "${environment}"
fi
for var in TESLAMATE_GRAFANA_URL TESLAMATE_GRAFANA_TOKEN; do
  if [[ -z "${!var:-}" ]]; then
    echo "error: ${var} is not set; run chezmoi apply" >&2
    exit 1
  fi
done

if [[ $# -ne 1 || "$1" != /api/* ]]; then
  echo "usage: bash api.sh /api/<path>" >&2
  exit 1
fi

body="$(mktemp)"
trap 'command rm -f "${body}"' EXIT
status="$(
  curl -sS -o "${body}" -w '%{http_code}' \
    -H "Authorization: Bearer ${TESLAMATE_GRAFANA_TOKEN}" \
    "${TESLAMATE_GRAFANA_URL}$1"
)"
if [[ "${status}" != 2* ]]; then
  echo "error: HTTP ${status}: $(cat "${body}")" >&2
  exit 1
fi
cat "${body}"

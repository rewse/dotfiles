#!/usr/bin/env bash
# Run a SQL query against the TeslaMate PostgreSQL datasource through Grafana's
# /api/ds/query and print the result as TSV with a header row.
#
# Usage: bash query.sh 'SELECT ...'
#        bash query.sh < query.sql
#
# The query runs inside a READ ONLY transaction as a second guard behind the
# datasource's SELECT-only role. Grafana returns timestamp columns as epoch
# milliseconds, read as UTC wall-clock time; they are printed as
# "YYYY-MM-DD HH:MM:SS" with no zone, so a column already shifted to JST
# prints JST. An empty result prints "(0 rows)" on stderr. Errors go to stderr
# with exit status 1.
set -euo pipefail

readonly DATASOURCE_UID="PC98BA2F4D77E1A42"

# A shell started before ~/.zshenv gained these exports lacks them; a
# non-interactive zsh reads ~/.zshenv without the zshrc output noise.
for var in TESLAMATE_GRAFANA_URL TESLAMATE_GRAFANA_TOKEN; do
  if [[ -z "${!var:-}" ]]; then
    printf -v "${var}" '%s' "$(zsh -c "print -r -- \$${var}")"
  fi
  if [[ -z "${!var}" ]]; then
    echo "error: ${var} is not set; run chezmoi apply" >&2
    exit 1
  fi
done

if [[ $# -gt 0 ]]; then
  sql="$1"
else
  sql="$(cat)"
fi

# Statements that could leave the READ ONLY transaction are refused.
if grep -Eiq '\b(abort|commit|rollback|read[[:space:]]+write)\b' <<<"${sql}"; then
  echo "error: transaction control is not allowed; send a single read query" >&2
  exit 1
fi
sql="$(sed -E 's/[[:space:];]+$//' <<<"${sql}")"

response="$(
  jq -n --arg sql "BEGIN READ ONLY; ${sql}; COMMIT" --arg uid "${DATASOURCE_UID}" \
    '{queries: [{refId: "A", datasource: {uid: $uid}, rawSql: $sql, format: "table"}]}' |
    curl -sS \
      -H "Authorization: Bearer ${TESLAMATE_GRAFANA_TOKEN}" \
      -H "Content-Type: application/json" \
      --data-binary @- \
      "${TESLAMATE_GRAFANA_URL}/api/ds/query"
)"

jq -r '
  if (.results.A | type) != "object" then
    ("error: " + (.message // tostring) + "\n" | halt_error(1))
  elif .results.A.error then
    ("error: " + .results.A.error + "\n" | halt_error(1))
  else . end
  | (.results.A.frames[0] // {}) as $f
  | [$f.schema.fields[]?] as $fields
  | if ($fields | length) == 0 or (($f.data.values[0] // []) | length) == 0 then
      ("(0 rows)\n" | stderr | empty)
    else
      ($fields | map(.name) | @tsv),
      ($f.data.values | transpose[]
        | [to_entries[] | .key as $i | .value
            | if . == null then ""
              elif $fields[$i].type == "time" then
                (. / 1000 | floor | strftime("%Y-%m-%d %H:%M:%S"))
              else tostring end]
        | @tsv)
    end
' <<<"${response}"

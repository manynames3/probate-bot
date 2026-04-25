#!/usr/bin/env bash
set -euo pipefail

: "${APP_DIR:?APP_DIR must be set}"
: "${PROBATE_BOT_DB:?PROBATE_BOT_DB must be set}"

STATE="${PROBATE_BOT_SYNC_STATE:-ga}"
MODE="${PROBATE_BOT_SYNC_MODE:-explicit}"
COUNTIES="${PROBATE_BOT_SYNC_COUNTIES:-Hall,Henry,Douglas,Cobb}"
DAYS_BACK="${PROBATE_BOT_SYNC_DAYS_BACK:-1}"
DATE_FIELD="${PROBATE_BOT_SYNC_DATE_FIELD:-filed}"
MAX_RESULTS="${PROBATE_BOT_SYNC_MAX_RESULTS:-100}"

cmd=(
  "${APP_DIR}/.venv/bin/probate-bot"
  sync
  --state "${STATE}"
  --db "${PROBATE_BOT_DB}"
  --date-field "${DATE_FIELD}"
  --max-results-per-county "${MAX_RESULTS}"
)

if [[ -n "${DAYS_BACK}" ]]; then
  cmd+=(--days-back "${DAYS_BACK}")
fi

if [[ "${MODE}" == "all-convenient" ]]; then
  cmd+=(--all-convenient)
else
  IFS=',' read -r -a county_list <<< "${COUNTIES}"
  for county in "${county_list[@]}"; do
    trimmed="$(printf '%s' "${county}" | xargs)"
    if [[ -n "${trimmed}" ]]; then
      cmd+=(--county "${trimmed}")
    fi
  done
fi

exec "${cmd[@]}"

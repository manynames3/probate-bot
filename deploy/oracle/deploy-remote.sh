#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 || $# -gt 2 ]]; then
  echo "Usage: deploy/oracle/deploy-remote.sh <user@host> [app-dir]" >&2
  exit 2
fi

TARGET="$1"
APP_DIR="${2:-/opt/probate-bot}"
REMOTE_USER="${TARGET%@*}"

if [[ "${REMOTE_USER}" == "${TARGET}" ]]; then
  echo "Target must include the SSH user, for example ubuntu@129.146.1.23" >&2
  exit 2
fi

ssh "${TARGET}" "sudo mkdir -p '${APP_DIR}' && sudo chown '${REMOTE_USER}':'${REMOTE_USER}' '${APP_DIR}'"

rsync -az --delete \
  --exclude '.git' \
  --exclude '.venv' \
  --exclude '__pycache__' \
  --exclude '.pytest_cache' \
  --exclude 'tmp' \
  --exclude '.DS_Store' \
  ./ "${TARGET}:${APP_DIR}/"

ssh "${TARGET}" "cd '${APP_DIR}' && APP_DIR='${APP_DIR}' APP_USER='${REMOTE_USER}' DB_PATH='${APP_DIR}/data/probate.sqlite' bash deploy/oracle/bootstrap.sh"

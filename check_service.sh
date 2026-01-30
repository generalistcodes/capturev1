#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

VENV_DIR="${VENV_DIR:-$ROOT_DIR/.venv}"
CLI_BIN="$VENV_DIR/bin/cli-driver-axiom"

ENV_FILE="${ENV_FILE:-$ROOT_DIR/.env}"
ALT_ENV_FILE="${ALT_ENV_FILE:-$ROOT_DIR/axiom.env}"

load_env_file() {
  local f="$1"
  [[ -f "$f" ]] || return 0
  while IFS= read -r line || [[ -n "$line" ]]; do
    [[ "$line" =~ ^[[:space:]]*# ]] && continue
    [[ "$line" =~ ^[[:space:]]*$ ]] && continue
    if [[ "$line" =~ ^[A-Za-z_][A-Za-z0-9_]*= ]]; then
      local key="${line%%=*}"
      local val="${line#*=}"
      val="${val%\"}"; val="${val#\"}"
      val="${val%\'}"; val="${val#\'}"
      export "$key=$val"
    fi
  done < "$f"
}

if [[ -f "$ENV_FILE" ]]; then
  load_env_file "$ENV_FILE"
elif [[ -f "$ALT_ENV_FILE" ]]; then
  load_env_file "$ALT_ENV_FILE"
fi

AXIOM_OUT_DIR="${AXIOM_OUT_DIR:-$ROOT_DIR/axiom_service_out}"
PIDFILE="${AXIOM_PIDFILE:-$AXIOM_OUT_DIR/cli-driver-axiom.pid}"
CHECKPOINT_CSV="${AXIOM_CHECKPOINT_CSV:-$AXIOM_OUT_DIR/axiom_checkpoints.csv}"

echo "out_dir:        $AXIOM_OUT_DIR"
echo "pidfile:        $PIDFILE"
echo "checkpoint_csv: $CHECKPOINT_CSV"

if [[ ! -x "$CLI_BIN" ]]; then
  echo "cli-driver-axiom not installed (missing $CLI_BIN). Run: ./start.sh"
  exit 2
fi

set +e
"$CLI_BIN" status --dir "$AXIOM_OUT_DIR"
STATUS_CODE=$?
set -e

if [[ -f "$PIDFILE" ]]; then
  PID="$(head -n 1 "$PIDFILE" 2>/dev/null || true)"
  echo "pid:            ${PID:-<empty>}"
else
  echo "pid:            <no pidfile>"
fi

if [[ -f "$CHECKPOINT_CSV" ]]; then
  CAPTURES="$(awk -F',' 'NR>1 && $1=="capture"{c++} END{print c+0}' "$CHECKPOINT_CSV")"
  LAST_LINE="$(tail -n 1 "$CHECKPOINT_CSV" 2>/dev/null || true)"
  echo "captures:       $CAPTURES"
  echo "last_checkpoint:$LAST_LINE"
else
  echo "captures:       0"
  echo "last_checkpoint:<none>"
fi

exit "$STATUS_CODE"


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

AXIOM_OUT_DIR="${AXIOM_OUT_DIR:-$ROOT_DIR/captures}"
export AXIOM_OUT_DIR

TIMEOUT="${TIMEOUT:-5}"
FORCE="${FORCE:-0}"

if [[ ! -x "$CLI_BIN" ]]; then
  echo "cli-driver-axiom not installed (missing $CLI_BIN)."
  exit 2
fi

ARGS=(stop --dir "$AXIOM_OUT_DIR" --timeout "$TIMEOUT")
if [[ "$FORCE" == "1" ]]; then
  ARGS+=(--force)
fi

"$CLI_BIN" "${ARGS[@]}"


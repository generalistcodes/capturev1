#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

VENV_DIR="${VENV_DIR:-$ROOT_DIR/.venv}"
CLI_BIN="$VENV_DIR/bin/cli-driver-axiom"
PY_BIN="$VENV_DIR/bin/python"

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
      # trim surrounding quotes if present
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

if [[ ! -x "$CLI_BIN" ]]; then
  echo "Creating venv and installing cli-driver-axiom..."
  python3 -m venv "$VENV_DIR"
  "$PY_BIN" -m pip install -U pip >/dev/null
  "$PY_BIN" -m pip install -e . >/dev/null
fi

AXIOM_OUT_DIR="${AXIOM_OUT_DIR:-$ROOT_DIR/captures}"
export AXIOM_OUT_DIR
mkdir -p "$AXIOM_OUT_DIR"

LOG_FILE="${LOG_FILE:-$AXIOM_OUT_DIR/driver.log}"
PIDFILE="${AXIOM_PIDFILE:-$AXIOM_OUT_DIR/cli-driver-axiom.pid}"
CHECKPOINT_CSV="${AXIOM_CHECKPOINT_CSV:-$AXIOM_OUT_DIR/axiom_checkpoints.csv}"
SEND_MODE="${SEND_MODE:-git}"
GIT_REPO="${GIT_REPO:-$ROOT_DIR}"
GIT_REMOTE="${GIT_REMOTE:-origin}"
GIT_BRANCH="${GIT_BRANCH:-main}"
GIT_PUSH_EVERY="${GIT_PUSH_EVERY:-1}"

echo "Starting cli-driver-axiom as a background service..."
echo "out_dir:        $AXIOM_OUT_DIR"
echo "pidfile:        $PIDFILE"
echo "checkpoint_csv: $CHECKPOINT_CSV"
echo "log_file:       $LOG_FILE"
echo "send_mode:      $SEND_MODE"
echo "git_repo:       $GIT_REPO"

if "$CLI_BIN" status --dir "$AXIOM_OUT_DIR" --quiet; then
  echo "Already running."
  "$CLI_BIN" status --dir "$AXIOM_OUT_DIR"
  exit 0
fi

nohup "$CLI_BIN" driver \
  --dir "$AXIOM_OUT_DIR" \
  --send "$SEND_MODE" \
  --git-repo "$GIT_REPO" \
  --git-remote "$GIT_REMOTE" \
  --git-branch "$GIT_BRANCH" \
  --git-push-every "$GIT_PUSH_EVERY" \
  >"$LOG_FILE" 2>&1 &
sleep 0.2

if "$CLI_BIN" status --dir "$AXIOM_OUT_DIR" --quiet; then
  echo "RUNNING as service (detached). You can close this shell."
  "$CLI_BIN" status --dir "$AXIOM_OUT_DIR"
  exit 0
fi

echo "FAILED to start. Check log: $LOG_FILE"
exit 1


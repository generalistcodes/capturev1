#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

say() { printf "%s\n" "$*"; }
die() { say "ERROR: $*"; exit 1; }

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

preflight() {
  say "Preflight checks:"

  # CLI present
  if [[ -x "$CLI_BIN" ]]; then
    say "  [OK] cli installed: $CLI_BIN"
  else
    die "cli not installed (missing $CLI_BIN)"
  fi

  # Basic CLI functionality
  if "$CLI_BIN" --help >/dev/null 2>&1; then
    say "  [OK] cli responds to --help"
  else
    die "cli does not respond to --help"
  fi

  # Output dir writable
  if [[ -d "$AXIOM_OUT_DIR" && -w "$AXIOM_OUT_DIR" ]]; then
    say "  [OK] out_dir writable: $AXIOM_OUT_DIR"
  else
    die "out_dir is not writable: $AXIOM_OUT_DIR"
  fi

  # Repo checks if we intend to send via git
  if [[ "${SEND_MODE,,}" == "git" ]]; then
    command -v git >/dev/null 2>&1 || die "git not found in PATH"

    if git -C "$GIT_REPO" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
      say "  [OK] git repo: $GIT_REPO"
    else
      die "GIT_REPO is not a git repo: $GIT_REPO"
    fi

    if git -C "$GIT_REPO" remote get-url "$GIT_REMOTE" >/dev/null 2>&1; then
      REMOTE_URL="$(git -C "$GIT_REPO" remote get-url "$GIT_REMOTE")"
      say "  [OK] git remote '$GIT_REMOTE': $REMOTE_URL"
    else
      die "git remote '$GIT_REMOTE' not configured in $GIT_REPO"
    fi

    # Ensure captures are NOT ignored (git add would fail otherwise)
    touch "$AXIOM_OUT_DIR/.axiom_ignore_probe" || true
    if git -C "$GIT_REPO" check-ignore -q "$(realpath --relative-to="$GIT_REPO" "$AXIOM_OUT_DIR/.axiom_ignore_probe")" 2>/dev/null; then
      rm -f "$AXIOM_OUT_DIR/.axiom_ignore_probe" || true
      die "captures directory appears ignored by gitignore; cannot git-add screenshots. Check .gitignore rules."
    fi
    rm -f "$AXIOM_OUT_DIR/.axiom_ignore_probe" || true
    say "  [OK] captures are trackable (not ignored by gitignore)"

    # Verify remote auth works (no changes pushed)
    if git -C "$GIT_REPO" ls-remote -q "$GIT_REMOTE" HEAD >/dev/null 2>&1; then
      say "  [OK] repo access OK (git ls-remote succeeded)"
    else
      die "cannot access remote '$GIT_REMOTE' (auth/SSH key/token). Try: git -C \"$GIT_REPO\" ls-remote \"$GIT_REMOTE\""
    fi

    # Dry-run push to confirm push permission (safe: does not push)
    if git -C "$GIT_REPO" push --dry-run "$GIT_REMOTE" "HEAD:$GIT_BRANCH" >/dev/null 2>&1; then
      say "  [OK] push permission OK (dry-run)"
    else
      die "push permission failed (dry-run). Ensure you have write access to the repo and auth is configured."
    fi
  fi

  # PID sanity
  if [[ -f "$PIDFILE" ]]; then
    say "  [INFO] pidfile exists: $PIDFILE"
  else
    say "  [OK] pidfile path: $PIDFILE"
  fi

  # Print effective env for visibility
  say "Effective config:"
  say "  AXIOM_OUT_DIR=$AXIOM_OUT_DIR"
  say "  AXIOM_INTERVAL_SECONDS=${AXIOM_INTERVAL_SECONDS:-<default>}"
  say "  AXIOM_DISPLAY=${AXIOM_DISPLAY:-<default>}"
  say "  AXIOM_REGION=${AXIOM_REGION:-<none>}"
  say "  AXIOM_PIDFILE=${AXIOM_PIDFILE:-$PIDFILE}"
  say "  AXIOM_CHECKPOINT_CSV=${AXIOM_CHECKPOINT_CSV:-$CHECKPOINT_CSV}"
  say "  SEND_MODE=$SEND_MODE"
  say "  GIT_REPO=$GIT_REPO"
  say "  GIT_REMOTE=$GIT_REMOTE"
  say "  GIT_BRANCH=$GIT_BRANCH"
  say "  GIT_PUSH_EVERY=$GIT_PUSH_EVERY"

  say "Preflight: PASS"
}

echo "Starting cli-driver-axiom as a background service..."
echo "out_dir:        $AXIOM_OUT_DIR"
echo "pidfile:        $PIDFILE"
echo "checkpoint_csv: $CHECKPOINT_CSV"
echo "log_file:       $LOG_FILE"
echo "send_mode:      $SEND_MODE"
echo "git_repo:       $GIT_REPO"

preflight

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


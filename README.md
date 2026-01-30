## cli-driver-axiom

`cli-driver-axiom` is a small, clean CLI service that captures screenshots to a PNG file.

### Install (recommended: virtualenv)

Proposed commands:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e '.[dev]'
```

### Usage

- **Show displays / monitors**:

```bash
cli-driver-axiom info
```

- **Capture full display (default: display 1) to a timestamped PNG in the current directory**:

```bash
cli-driver-axiom capture
```

- **Capture a specific display to a specific output file**:

```bash
cli-driver-axiom capture --display 1 --out /tmp/screen.png
```

- **Capture a region (x y width height)**:

```bash
cli-driver-axiom capture --region 100 100 800 600 --out /tmp/region.png
```

### Send options (push screenshots somewhere)

By default, screenshots are only saved locally. You can also **send** each captured PNG using `--send`:

- **`--send none`**: save only (default)
- **`--send git`**: `git add/commit` (and optionally `git push`) the captured PNG into a repo
- **`--send curl`**: upload via `curl` multipart form (good for webhooks/APIs)

#### Send via Git (easiest if you already have a repo + auth)

Pre-req: the output directory (or `--git-repo`) must already be a git repo with a configured remote and working auth.

Example: commit+push each capture into a repo directory:

```bash
cli-driver-axiom capture --dir /tmp/axiom --send git --git-repo /path/to/repo --git-remote origin --git-branch main
```

Driver example: push every 10 captures (commit every capture; push batched):

```bash
cli-driver-axiom driver --dir /tmp/axiom --interval 2 --send git --git-repo /path/to/repo --git-push-every 10
```

If you only want commits locally (no push):

```bash
cli-driver-axiom driver --dir /tmp/axiom --send git --no-git-push
```

#### Send via API/Webhook using curl (easiest “API push”)

Upload the file as multipart form field `file`:

```bash
cli-driver-axiom capture --dir /tmp/axiom --send curl --curl-url 'https://example.com/upload' --curl-header 'Authorization: Bearer TOKEN'
```

Driver example:

```bash
cli-driver-axiom driver --dir /tmp/axiom --interval 5 --send curl --curl-url 'https://example.com/upload'
```

### Driver mode (runs as its own process)

Capture continuously every N seconds (stop with Ctrl+C):

```bash
cli-driver-axiom driver --dir /tmp/axiom-shots --interval 2
```

### Start/Check scripts (Linux/macOS)

If you want a simple “service-like” start that keeps running after the script exits:

- **Configure via `.env` (recommended)**:

```bash
cp axiom.env.example .env
# edit .env (AXIOM_INTERVAL_SECONDS=10s, etc.)
```

- **Start detached driver** (creates venv if missing, writes logs + pidfile + checkpoint CSV):

```bash
./start.sh
```

- **Check service** (prints status + pid + capture count + last checkpoint):

```bash
./check_service.sh
echo $?
```

- **Stop service** (stops driver by pidfile):

```bash
./stop.sh
```

Defaults used by scripts:
- `AXIOM_OUT_DIR`: `./captures`
- pidfile: `<out_dir>/cli-driver-axiom.pid`
- checkpoint CSV: `<out_dir>/axiom_checkpoints.csv`
- log file: `<out_dir>/driver.log`

Check if the driver is running (uses pidfile):

```bash
cli-driver-axiom status --dir /tmp/axiom-shots
echo $?
```

You can also configure via environment variables (CLI args override env):

- **`AXIOM_OUT_DIR`**: output directory (default: current directory)
- **`AXIOM_INTERVAL_SECONDS`**: capture interval seconds (default: `5.0`)
- **`AXIOM_DISPLAY`**: monitor index (default: `1`)
- **`AXIOM_REGION`**: region `"x y w h"` or `"x,y,w,h"` (optional)
- **`AXIOM_PIDFILE`**: optional pidfile path (prevents double-start if pidfile exists)
- **`AXIOM_FILENAME_PREFIX`**: filename prefix (default: `axiom_`)

Example using env vars:

```bash
export AXIOM_OUT_DIR=/tmp/axiom-shots
export AXIOM_INTERVAL_SECONDS=3
export AXIOM_DISPLAY=1
cli-driver-axiom driver
```

Optional: run it via systemd (user service) so it stays running after logout (Linux):

```ini
[Unit]
Description=cli-driver-axiom screenshot driver

[Service]
ExecStart=%h/.venv/bin/cli-driver-axiom driver
Environment=AXIOM_OUT_DIR=%h/Pictures/axiom
Environment=AXIOM_INTERVAL_SECONDS=5
Restart=always
RestartSec=2

[Install]
WantedBy=default.target
```

### Verify (quick)

Proposed commands:

```bash
pytest -q
cli-driver-axiom info
cli-driver-axiom capture --out /tmp/axiom.png
file /tmp/axiom.png
```


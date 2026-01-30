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

### Driver mode (runs as its own process)

Capture continuously every N seconds (stop with Ctrl+C):

```bash
cli-driver-axiom driver --dir /tmp/axiom-shots --interval 2
```

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


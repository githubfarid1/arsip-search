"""Docker container watchdog + restart service.

Uses Docker CLI via subprocess.
- Background thread checks if target container is running.
- If stopped/exited → restarts it.
- If missing (removed/never created) → recreates via 'docker run' (primary) or 'docker compose up' (fallback).
- Aggressive retry (30s) while down; back to CHECK_INTERVAL when healthy.
- Exposes POST / for manual trigger, GET /status and GET /health.
"""

import http.server
import json
import os
import subprocess
import threading
import time

CONTAINER_NAME = os.getenv("TARGET_CONTAINER", "arsip-api")
PORT = 9999
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "1800"))
RETRY_INTERVAL = int(os.getenv("RETRY_INTERVAL", "30"))

# --- docker run config (primary method for missing container) ---
TARGET_IMAGE = os.getenv("TARGET_IMAGE", "arsip-api:latest")
TARGET_NETWORK = os.getenv("TARGET_NETWORK", "")
TARGET_PORTS = os.getenv("TARGET_PORTS", "")          # "8888:8888" or ""
TARGET_ENV_FILE = os.getenv("TARGET_ENV_FILE", "")     # path to .env file
TARGET_ENV_VARS = os.getenv("TARGET_ENV_VARS", "")    # "K1=V1,K2=V2"
TARGET_VOLUMES = os.getenv("TARGET_VOLUMES", "")      # "/host:/container:opts,/host2:/c2"
TARGET_RESTART_POLICY = os.getenv("TARGET_RESTART_POLICY", "unless-stopped")

# --- docker compose config (fallback method) ---
COMPOSE_FILE = os.getenv("COMPOSE_FILE", "")
COMPOSE_SERVICE = os.getenv("COMPOSE_SERVICE", "api")
COMPOSE_PROJECT = os.getenv("COMPOSE_PROJECT_NAME", "")


def run_cmd(cmd, timeout=60):
    """Run a command. Returns (returncode, stdout, stderr)."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except FileNotFoundError:
        return -1, "", f"command not found: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return -1, "", "timeout"
    except Exception as e:
        return -1, "", str(e)


def get_container_status():
    """Return 'running', 'exited', 'created', 'dead', 'missing', or 'error: ...'."""
    code, out, err = run_cmd(["docker", "inspect", CONTAINER_NAME])
    if code != 0:
        if "No such object" in err or "No such container" in err:
            return "missing"
        return f"error: {err}"

    try:
        data = json.loads(out)
        if isinstance(data, list):
            if not data:
                return "missing"
            item = data[0]
        else:
            item = data

        state = item.get("State", {})
        if not isinstance(state, dict):
            print(f"[debug] State is not dict: {repr(state)}")
            return "unknown"

        status = state.get("Status")
        if not status:
            print(f"[debug] No Status in State. Keys: {list(state.keys())}")
            print(f"[debug] Raw inspect (first 500): {out[:500]}")
            return "unknown"
        return status
    except (json.JSONDecodeError, AttributeError, IndexError) as e:
        print(f"[debug] Parse error: {e}")
        print(f"[debug] Raw output (first 500): {out[:500]}")
        return f"error: bad inspect output ({e})"


def restart_container():
    code, out, err = run_cmd(["docker", "restart", "-t", "10", CONTAINER_NAME], timeout=60)
    return code == 0, err or out


def start_container():
    code, out, err = run_cmd(["docker", "start", CONTAINER_NAME], timeout=60)
    return code == 0, err or out


def docker_run_create():
    """Create + start container directly via docker run. Returns (ok, message)."""
    cmd = ["docker", "run", "-d",
           "--name", CONTAINER_NAME,
           "--restart", TARGET_RESTART_POLICY]

    if TARGET_NETWORK:
        cmd += ["--network", TARGET_NETWORK]

    if TARGET_PORTS:
        for p in TARGET_PORTS.split(","):
            p = p.strip()
            if p:
                cmd += ["-p", p]

    if TARGET_VOLUMES:
        for v in TARGET_VOLUMES.split(","):
            v = v.strip()
            if v:
                cmd += ["-v", v]

    if TARGET_ENV_FILE:
        cmd += ["--env-file", TARGET_ENV_FILE]

    if TARGET_ENV_VARS:
        for e in TARGET_ENV_VARS.split(","):
            e = e.strip()
            if e:
                cmd += ["-e", e]

    cmd.append(TARGET_IMAGE)

    cmd_str = " ".join(cmd)
    print(f"[docker-run] {cmd_str}")
    code, out, err = run_cmd(cmd, timeout=120)
    output = (out + " " + err).strip()

    # Handle name conflict: remove leftover and retry once
    if code != 0 and "already in use" in output:
        print(f"[docker-run] Name conflict! Removing leftover container...")
        run_cmd(["docker", "rm", "-f", CONTAINER_NAME], timeout=30)
        code, out, err = run_cmd(cmd, timeout=120)
        output = (out + " " + err).strip()

    return code == 0, output


def compose_up():
    """Create via docker compose. Returns (ok, message)."""
    if not COMPOSE_FILE:
        return False, "COMPOSE_FILE not set"

    base = ["docker", "compose", "-f", COMPOSE_FILE, "up", "-d"]
    if COMPOSE_PROJECT:
        base += ["-p", COMPOSE_PROJECT]

    for label, extra in [("with build", [COMPOSE_SERVICE]), ("no build", ["--no-build", COMPOSE_SERVICE])]:
        cmd = base + extra
        print(f"[compose] Trying ({label}): {' '.join(cmd)}")
        code, out, err = run_cmd(cmd, timeout=180)
        output = (out + " " + err).strip()

        # Handle name conflict: remove leftover and retry once
        if code != 0 and "already in use" in output:
            print(f"[compose] Name conflict! Removing leftover container...")
            run_cmd(["docker", "rm", "-f", CONTAINER_NAME], timeout=30)
            code, out, err = run_cmd(cmd, timeout=180)
            output = (out + " " + err).strip()

        if code == 0:
            print(f"[compose] ✓ Success ({label})")
            return True, output
        print(f"[compose] ✗ Failed ({label}): {output}")

    return False, output


def create_container():
    """Try to create missing container: compose first (managed), then docker run."""
    # Remove leftover container if any (from previous docker run or broken state)
    run_cmd(["docker", "rm", "-f", CONTAINER_NAME], timeout=30)

    # Method 1: docker compose (container is compose-managed, no deploy conflict)
    if COMPOSE_FILE:
        ok, msg = compose_up()
        if ok:
            return True, f"created via compose: {msg}"
        print(f"[watchdog] compose failed: {msg}")
        print(f"[watchdog] Trying docker run fallback...")

    # Method 2: docker run (unmanaged, last resort)
    ok2, msg2 = docker_run_create()
    if ok2:
        return True, f"created via docker run: {msg2}"

    return False, f"compose: {msg if COMPOSE_FILE else 'not configured'} | docker run: {msg2}"


def ensure_container():
    """Check and act on container status. Returns (status, healthy)."""
    status = get_container_status()
    ts = time.strftime("%Y-%m-%d %H:%M:%S")

    if status == "running":
        print(f"[watchdog] {ts} — {CONTAINER_NAME}: running ✓")
        return status, True

    if status in ("exited", "created", "dead"):
        print(f"[watchdog] {ts} — {CONTAINER_NAME}: {status}! Restarting...")
        ok, msg = restart_container()
        if ok:
            print(f"[watchdog] {ts} — {CONTAINER_NAME}: restarted ✓")
            return status, True
        print(f"[watchdog] {ts} — restart failed ({msg}), trying start...")
        ok2, msg2 = start_container()
        if ok2:
            print(f"[watchdog] {ts} — {CONTAINER_NAME}: started ✓")
            return status, True
        print(f"[watchdog] {ts} — restart/start FAILED: '{msg}' | '{msg2}'")
        return status, False

    if status in ("missing", "unknown") or status.startswith("error"):
        print(f"[watchdog] {ts} — {CONTAINER_NAME}: {status}! Recreating...")
        ok, msg = create_container()
        if ok:
            print(f"[watchdog] {ts} — {CONTAINER_NAME}: {msg}")
            return status, True
        print(f"[watchdog] {ts} — {CONTAINER_NAME}: recreate FAILED: {msg}")
        return status, False

    print(f"[watchdog] {ts} — {CONTAINER_NAME}: {status}")
    return status, False


def watchdog_loop():
    time.sleep(5)
    print(f"[watchdog] Started. target='{CONTAINER_NAME}' interval={CHECK_INTERVAL}s retry={RETRY_INTERVAL}s")
    print(f"[watchdog] Create config: image={TARGET_IMAGE} network={TARGET_NETWORK} ports={TARGET_PORTS}")
    print(f"[watchdog] Volumes: {TARGET_VOLUMES}")
    print(f"[watchdog] EnvFile: {TARGET_ENV_FILE} EnvVars: {'yes' if TARGET_ENV_VARS else 'no'}")

    while True:
        try:
            status, healthy = ensure_container()
            if healthy:
                time.sleep(CHECK_INTERVAL)
            else:
                print(f"[watchdog] Unhealthy, retrying in {RETRY_INTERVAL}s...")
                time.sleep(RETRY_INTERVAL)
        except Exception as e:
            print(f"[watchdog] Error: {e}")
            time.sleep(RETRY_INTERVAL)


class Handler(http.server.BaseHTTPRequestHandler):

    def do_POST(self):
        status = get_container_status()
        if status == "running":
            self._respond(200, {"status": "ok", "message": f"'{CONTAINER_NAME}' already running"})
        elif status == "missing":
            ok, msg = create_container()
            self._respond(200 if ok else 500, {"status": "ok" if ok else "error", "message": msg})
        else:
            ok, msg = restart_container()
            if not ok:
                ok2, msg2 = start_container()
                if ok2:
                    self._respond(200, {"status": "ok", "message": f"'{CONTAINER_NAME}' started"})
                else:
                    self._respond(500, {"status": "error", "message": f"restart: {msg} | start: {msg2}"})
            else:
                self._respond(200, {"status": "ok", "message": f"'{CONTAINER_NAME}' restarted"})

    def do_GET(self):
        if self.path == "/health":
            self._respond(200, {"status": "ok"})
        elif self.path == "/status":
            self._respond(200, {"container": CONTAINER_NAME, "status": get_container_status()})
        else:
            self._respond(405, {"status": "error", "message": "Use POST / or GET /status"})

    def _respond(self, status, body):
        payload = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format, *args):
        print(f"[http] {args[0]}")


if __name__ == "__main__":
    t = threading.Thread(target=watchdog_loop, daemon=True)
    t.start()

    server = http.server.HTTPServer(("0.0.0.0", PORT), Handler)
    print(f"[http] Listening on :{PORT}, target={CONTAINER_NAME}")
    server.serve_forever()

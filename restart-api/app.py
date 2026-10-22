"""Docker container watchdog + restart service.

Uses Docker CLI via subprocess (already installed in image).
- Background thread checks if target container is running.
- If stopped/exited, automatically restarts it.
- If missing (never created), calls docker compose up to recreate it.
- Aggressive retry (30s) while target is down; back to CHECK_INTERVAL when healthy.
- Also exposes POST / for manual restart trigger and GET /status.
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
COMPOSE_FILE = os.getenv("COMPOSE_FILE", "/app/docker-compose.yml")
COMPOSE_SERVICE = os.getenv("COMPOSE_SERVICE", "api")
COMPOSE_PROJECT = os.getenv("COMPOSE_PROJECT_NAME", "arsip-search")


def run_docker(*args, timeout=30):
    """Run a docker CLI command. Returns (returncode, stdout, stderr)."""
    cmd = ["docker"] + list(args)
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except FileNotFoundError:
        return -1, "", "docker CLI not found"
    except subprocess.TimeoutExpired:
        return -1, "", "timeout"
    except Exception as e:
        return -1, "", str(e)


def get_container_status():
    """Return 'running', 'exited', 'created', 'dead', 'missing', or 'error: ...'."""
    code, out, err = run_docker("inspect", "-f", "{{.State.Status}}", CONTAINER_NAME)
    if code == 0:
        return out
    if "No such object" in err or "No such container" in err:
        return "missing"
    return f"error: {err}"


def restart_container():
    """Restart the container. Returns (ok, message)."""
    code, out, err = run_docker("restart", "-t", "10", CONTAINER_NAME, timeout=60)
    return code == 0, err or out


def start_container():
    """Start a stopped container. Returns (ok, message)."""
    code, out, err = run_docker("start", CONTAINER_NAME, timeout=60)
    return code == 0, err or out


def compose_up():
    """Create/start a missing container via docker compose. Returns (ok, message)."""
    base = [
        "docker", "compose",
        "-f", COMPOSE_FILE,
        "-p", COMPOSE_PROJECT,
        "up", "-d",
    ]
    results = []

    for label, cmd in [
        ("with build", base + [COMPOSE_SERVICE]),
        ("no build", base + ["--no-build", COMPOSE_SERVICE]),
    ]:
        cmd_str = " ".join(cmd)
        print(f"[compose] Trying ({label}): {cmd_str}")
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
            output = (r.stdout + r.stderr).strip()
            if r.returncode == 0:
                print(f"[compose] ✓ Success ({label})")
                return True, output
            results.append(f"[{label}] rc={r.returncode}: {output}")
            print(f"[compose] ✗ Failed ({label}): {output}")
        except FileNotFoundError:
            return False, "docker CLI not found"
        except subprocess.TimeoutExpired:
            results.append(f"[{label}] timeout")
            print(f"[compose] ✗ Timeout ({label})")
        except Exception as e:
            results.append(f"[{label}] {e}")
            print(f"[compose] ✗ Error ({label}): {e}")

    return False, " | ".join(results)


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
        print(f"[watchdog] {ts} — FAILED: restart='{msg}' start='{msg2}'")
        return status, False

    if status == "missing":
        print(f"[watchdog] {ts} — {CONTAINER_NAME}: missing! Running docker compose up...")
        ok, msg = compose_up()
        if ok:
            print(f"[watchdog] {ts} — {CONTAINER_NAME}: created via compose ✓")
            return status, True
        print(f"[watchdog] {ts} — compose up failed: {msg}")
        return status, False

    print(f"[watchdog] {ts} — {CONTAINER_NAME}: {status}")
    return status, False


def watchdog_loop():
    time.sleep(5)
    print(f"[watchdog] Started. target='{CONTAINER_NAME}' interval={CHECK_INTERVAL}s retry={RETRY_INTERVAL}s")

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
            ok, msg = compose_up()
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

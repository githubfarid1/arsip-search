"""Docker container watchdog + restart service.

- Background thread checks if target container is running.
- If stopped/exited, automatically restarts it.
- If missing (never created), calls docker compose up to recreate it.
- Aggressive retry (30s) while target is down; back to CHECK_INTERVAL when healthy.
- Also exposes POST / for manual restart trigger.
- Uses only Python stdlib — no pip dependencies.
"""

import http.server
import json
import socket
import os
import subprocess
import threading
import time

CONTAINER_NAME = os.getenv("TARGET_CONTAINER", "arsip-api")
DOCKER_SOCKET = "/var/run/docker.sock"
PORT = 9999
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "1800"))  # normal interval
RETRY_INTERVAL = int(os.getenv("RETRY_INTERVAL", "30"))     # retry saat container mati
COMPOSE_FILE = os.getenv("COMPOSE_FILE", "/app/docker-compose.yml")
COMPOSE_SERVICE = os.getenv("COMPOSE_SERVICE", "api")
COMPOSE_PROJECT = os.getenv("COMPOSE_PROJECT_NAME", "arsip-search")


class DockerClient:
    """Minimal Docker Engine API client via unix socket."""

    def __init__(self, socket_path):
        self.socket_path = socket_path
        self._api_version = None

    def _raw_request(self, method, path, body=b""):
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(self.socket_path)
        sock.settimeout(30)
        headers = f"{method} {path} HTTP/1.1\r\nHost: localhost\r\n"
        if body:
            headers += f"Content-Length: {len(body)}\r\n"
        else:
            headers += "Content-Length: 0\r\n"
        headers += "\r\n"
        sock.sendall(headers.encode() + body)
        response = b""
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            response += chunk
        sock.close()
        status_line = response.split(b"\r\n")[0].decode(errors="replace")
        status_code = int(status_line.split(" ")[1]) if " " in status_line else 0
        parts = response.split(b"\r\n\r\n", 1)
        body_str = parts[1].decode(errors="replace") if len(parts) > 1 else ""
        return status_code, body_str

    def _api_prefix(self):
        """Detect Docker API version. Falls back to v1.41 (Docker 20.10+)."""
        if self._api_version:
            return self._api_version
        try:
            code, body = self._raw_request("GET", "/version")
            if code == 200:
                data = json.loads(body)
                ver = data.get("ApiVersion", "1.41")
                self._api_version = f"/v{ver}"
                return self._api_version
        except Exception:
            pass
        self._api_version = "/v1.41"
        return self._api_version

    def get_container_status(self, name):
        """Return container status string (e.g. 'running', 'exited', 'missing')."""
        try:
            prefix = self._api_prefix()
            code, body = self._raw_request("GET", f"{prefix}/containers/{name}/json")
            if code == 200:
                data = json.loads(body)
                return data.get("State", {}).get("Status", "unknown")
            elif code == 404:
                return "missing"
            else:
                return f"error({code})"
        except Exception as e:
            return f"error({e})"

    def restart_container(self, name):
        """Restart container. Returns (success, status_code)."""
        prefix = self._api_prefix()
        code, _ = self._raw_request("POST", f"{prefix}/containers/{name}/restart?t=10")
        return 200 <= code < 300, code

    def start_container(self, name):
        """Start a stopped container. Returns (success, status_code)."""
        prefix = self._api_prefix()
        code, _ = self._raw_request("POST", f"{prefix}/containers/{name}/start")
        return 200 <= code < 300, code


def compose_up():
    """Call docker compose up -d to create/start a missing container."""
    cmd = [
        "docker", "compose",
        "-f", COMPOSE_FILE,
        "-p", COMPOSE_PROJECT,
        "up", "-d", "--no-build", COMPOSE_SERVICE,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        output = (result.stdout + result.stderr).strip()
        return result.returncode == 0, output
    except FileNotFoundError:
        return False, "docker CLI not found"
    except subprocess.TimeoutExpired:
        return False, "docker compose timed out"
    except Exception as e:
        return False, str(e)


def ensure_container():
    """Check container status and take action. Returns (status, healthy: bool)."""
    client = DockerClient(DOCKER_SOCKET)
    status = client.get_container_status(CONTAINER_NAME)
    ts = time.strftime("%Y-%m-%d %H:%M:%S")

    if status == "running":
        print(f"[watchdog] {ts} — {CONTAINER_NAME}: running ✓")
        return status, True

    elif status in ("exited", "created", "dead"):
        print(f"[watchdog] {ts} — {CONTAINER_NAME}: {status}! Attempting restart...")
        ok, code = client.restart_container(CONTAINER_NAME)
        if ok:
            print(f"[watchdog] {ts} — {CONTAINER_NAME}: restarted successfully ✓")
            return status, True
        print(f"[watchdog] {ts} — {CONTAINER_NAME}: restart failed (code {code}), trying start...")
        ok2, code2 = client.start_container(CONTAINER_NAME)
        if ok2:
            print(f"[watchdog] {ts} — {CONTAINER_NAME}: started successfully ✓")
            return status, True
        print(f"[watchdog] {ts} — {CONTAINER_NAME}: restart/start FAILED (code {code}/{code2})")
        return status, False

    elif status == "missing":
        print(f"[watchdog] {ts} — {CONTAINER_NAME}: missing! Calling docker compose up...")
        ok, output = compose_up()
        if ok:
            print(f"[watchdog] {ts} — {CONTAINER_NAME}: created via compose ✓")
            return status, True
        print(f"[watchdog] {ts} — {CONTAINER_NAME}: compose up failed: {output}")
        return status, False

    else:
        print(f"[watchdog] {ts} — {CONTAINER_NAME}: {status}")
        return status, False


def watchdog_loop():
    """Background loop: check container, retry aggressively if down."""
    time.sleep(5)  # brief startup delay
    print(f"[watchdog] Started. target='{CONTAINER_NAME}' interval={CHECK_INTERVAL}s retry={RETRY_INTERVAL}s")

    while True:
        try:
            status, healthy = ensure_container()
            if healthy:
                time.sleep(CHECK_INTERVAL)
            else:
                print(f"[watchdog] Target unhealthy, retrying in {RETRY_INTERVAL}s...")
                time.sleep(RETRY_INTERVAL)
        except Exception as e:
            print(f"[watchdog] Error: {e}")
            time.sleep(RETRY_INTERVAL)


class Handler(http.server.BaseHTTPRequestHandler):
    """HTTP handler for manual restart trigger."""

    def do_POST(self):
        try:
            client = DockerClient(DOCKER_SOCKET)
            status = client.get_container_status(CONTAINER_NAME)
            if status == "running":
                self._respond(200, {"status": "ok", "message": f"'{CONTAINER_NAME}' already running"})
            elif status == "missing":
                ok, output = compose_up()
                if ok:
                    self._respond(200, {"status": "ok", "message": f"'{CONTAINER_NAME}' created via compose"})
                else:
                    self._respond(500, {"status": "error", "message": f"compose up failed: {output}"})
            else:
                ok, code = client.restart_container(CONTAINER_NAME)
                if ok:
                    self._respond(200, {"status": "ok", "message": f"'{CONTAINER_NAME}' restarted"})
                else:
                    ok2, code2 = client.start_container(CONTAINER_NAME)
                    if ok2:
                        self._respond(200, {"status": "ok", "message": f"'{CONTAINER_NAME}' started"})
                    else:
                        self._respond(500, {"status": "error", "message": f"Failed (code {code}/{code2})"})
        except Exception as e:
            self._respond(500, {"status": "error", "message": str(e)})

    def do_GET(self):
        if self.path == "/health":
            self._respond(200, {"status": "ok"})
        elif self.path == "/status":
            try:
                client = DockerClient(DOCKER_SOCKET)
                status = client.get_container_status(CONTAINER_NAME)
                self._respond(200, {"container": CONTAINER_NAME, "status": status})
            except Exception as e:
                self._respond(500, {"status": "error", "message": str(e)})
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

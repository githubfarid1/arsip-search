"""Lightweight Docker container restart service.

Exposes POST / to restart the arsip-api container via Docker Engine API.
Uses only Python stdlib — no pip dependencies.
"""

import http.server
import json
import socket
import os

CONTAINER_NAME = os.getenv("TARGET_CONTAINER", "arsip-api")
DOCKER_SOCKET = "/var/run/docker.sock"
PORT = 9999


class UnixSocketHTTPConnection:
    """Minimal HTTP client that talks to Docker Engine via unix socket."""

    def __init__(self, socket_path):
        self.socket_path = socket_path

    def request(self, method, path, body=None, headers=None):
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(self.socket_path)
        sock.settimeout(30)

        headers = headers or {}
        if body:
            headers["Content-Length"] = str(len(body))
        headers["Host"] = "localhost"

        raw = f"{method} {path} HTTP/1.1\r\n"
        for k, v in headers.items():
            raw += f"{k}: {v}\r\n"
        raw += "\r\n"
        if body:
            raw += body
        sock.sendall(raw.encode())

        response = b""
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            response += chunk
        sock.close()
        return response

    def restart_container(self, name):
        raw = self.request("POST", f"/v1.47/containers/{name}/restart?t=5")
        status_line = raw.split(b"\r\n")[0].decode(errors="replace")
        status_code = int(status_line.split(" ")[1]) if " " in status_line else 0
        return 200 <= status_code < 300, status_code


class Handler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            client = UnixSocketHTTPConnection(DOCKER_SOCKET)
            ok, code = client.restart_container(CONTAINER_NAME)
            if ok:
                self._respond(200, {"status": "ok", "message": f"Container '{CONTAINER_NAME}' restarted"})
            else:
                self._respond(500, {"status": "error", "message": f"Docker returned status {code}"})
        except FileNotFoundError:
            self._respond(500, {"status": "error", "message": "Docker socket not found"})
        except Exception as e:
            self._respond(500, {"status": "error", "message": str(e)})

    def do_GET(self):
        if self.path == "/health":
            self._respond(200, {"status": "ok"})
        else:
            self._respond(405, {"status": "error", "message": "Use POST / to restart"})

    def _respond(self, status, body):
        payload = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format, *args):
        print(f"[restart-api] {args[0]}")


if __name__ == "__main__":
    server = http.server.HTTPServer(("0.0.0.0", PORT), Handler)
    print(f"[restart-api] Listening on :{PORT}, target={CONTAINER_NAME}")
    server.serve_forever()
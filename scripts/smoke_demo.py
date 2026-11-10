"""Controlled local smoke test: starts and stops only its own demo processes."""
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]


def free_ports():
    sockets = [socket.socket(), socket.socket()]
    try:
        for sock in sockets:
            sock.bind(("127.0.0.1", 0))
        return [sock.getsockname()[1] for sock in sockets]
    finally:
        for sock in sockets:
            sock.close()


def request(base, path, payload=None, headers=None):
    data = None if payload is None else json.dumps(payload).encode()
    req = Request(base + path, data=data, headers=headers or {})
    try:
        with urlopen(req, timeout=3) as response:
            body = response.read()
            return response.status, response.headers, body
    except HTTPError as error:
        return error.code, error.headers, error.read()


def main():
    backend, frontend = free_ports()
    env = dict(os.environ, BUILDSEC_BACKEND_PORT=str(backend), BUILDSEC_FRONTEND_PORT=str(frontend))
    with tempfile.TemporaryFile(mode="w+") as log:
        process = subprocess.Popen(["./scripts/run.sh", "demo"], cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
        try:
            deadline = time.monotonic() + 15
            while time.monotonic() < deadline:
                log.seek(0)
                if f"Frontend listening on http://127.0.0.1:{frontend}" in log.read():
                    break
                if process.poll() is not None:
                    raise RuntimeError("Demo stack exited during startup")
                time.sleep(0.1)
            else:
                raise RuntimeError("Demo stack startup timed out")
            base = f"http://127.0.0.1:{frontend}"
            status, _, _ = request(base, "/")
            assert status == 200
            status, _, body = request(base, "/runtime/info")
            assert status == 200 and json.loads(body)["mode"] == "demo"
            status, headers, body = request(base, "/executions", {"goal": "health", "requiredChecks": ["F-01"], "workspace": "unused", "revision": "test"}, {"Content-Type": "application/json", "Prefer": "respond-async"})
            execution = json.loads(body)
            location = headers.get("Location")
            assert status == 202 and location == "/executions/" + execution["id"] and execution["state"] == "CREATED"
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                status, _, body = request(base, location)
                snapshot = json.loads(body)
                assert status == 200
                if snapshot["state"] in ("FAILED", "COMPLETED", "BLOCKED", "CANCELLED"):
                    break
                time.sleep(0.05)
            assert snapshot["state"] == "FAILED" and "GENERATING" in snapshot["history"]
            status, _, body = request(base, location + "/results")
            result = json.loads(body)
            assert status == 200 and result["state"] == "FAILED" and result["validation"][0]["status"] == "skipped"
            assert result["artifacts"] == [] and result["evidence"] == []
            status, _, body = request(base, "/executions")
            assert status == 200 and any(item["id"] == execution["id"] for item in json.loads(body)["executions"])
            assert request(base, "/executions/missing")[0] == 404
            assert request(base, "/executions", {}, {"Content-Type": "application/json"})[0] == 400
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
                raise RuntimeError("Demo stack did not shut down")
        for port in (backend, frontend):
            with socket.socket() as sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind(("127.0.0.1", port))
    print("Demo stack smoke test passed; both ports released.")


if __name__ == "__main__":
    main()
